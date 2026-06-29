from datetime import date, datetime
import calendar
import pandas as pd
import streamlit as st

from database import (
    init_db, seed_demo_data, get_df, run, execute, scalar,
    add_employee, add_brand, add_process, add_pod, add_assignment,
    set_availability, add_holiday, save_roster_rows, clear_roster_month,
)
from scheduler import generate_roster, validate_roster

st.set_page_config(page_title="Smart Roster Manager", page_icon="📅", layout="wide")
init_db()
if scalar("SELECT COUNT(*) FROM employees") == 0:
    seed_demo_data()

st.title("📅 Smart Roster Manager")
st.caption("Datastaw AI + Tech Internship Assessment · Starter implementation")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Open section",
        ["Dashboard", "Generate roster", "Roster views", "Manage data", "Availability & holidays", "How it works"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Demo data is fictional. Use Manage data to customize it.")

if page == "Dashboard":
    st.subheader("Operations overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Employees", scalar("SELECT COUNT(*) FROM employees WHERE active=1"))
    c2.metric("Brands", scalar("SELECT COUNT(*) FROM brands WHERE active=1"))
    c3.metric("Processes", scalar("SELECT COUNT(*) FROM processes WHERE active=1"))
    c4.metric("Assignments", scalar("SELECT COUNT(*) FROM assignments WHERE active=1"))
    st.divider()
    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Employees by pod")
        st.dataframe(get_df("""
            SELECT p.name AS pod, COUNT(e.id) AS employees
            FROM pods p LEFT JOIN employees e ON e.pod_id=p.id AND e.active=1
            GROUP BY p.id, p.name ORDER BY p.name
        """), use_container_width=True, hide_index=True)
    with right:
        st.markdown("#### Brand operating rules")
        st.dataframe(get_df("""
            SELECT b.name AS brand, b.operating_rule,
                   COUNT(DISTINCT a.employee_id) AS assigned_employees
            FROM brands b LEFT JOIN assignments a ON a.brand_id=b.id AND a.active=1
            WHERE b.active=1 GROUP BY b.id, b.name, b.operating_rule ORDER BY b.name
        """), use_container_width=True, hide_index=True)
    st.info("Start with **Generate roster**. Generate a month, review validation warnings, then test a change under Availability & holidays.")

elif page == "Generate roster":
    st.subheader("Generate monthly roster")
    today = date.today()
    col1, col2 = st.columns(2)
    month = col1.selectbox("Month", list(range(1, 13)), index=today.month - 1,
                           format_func=lambda m: calendar.month_name[m])
    year = col2.number_input("Year", min_value=2024, max_value=2035, value=today.year, step=1)
    st.caption("The generator considers brand/process working days, assignments, weekly offs, approved leave, holidays, minimum coverage, and one assignment per employee per day.")
    if st.button("Generate roster", type="primary", use_container_width=True):
        rows, issues = generate_roster(int(year), int(month))
        clear_roster_month(int(year), int(month))
        save_roster_rows(rows)
        st.session_state["last_generated"] = (int(year), int(month))
        st.session_state["last_issues"] = issues
        st.success(f"Generated {len(rows)} roster rows for {calendar.month_name[int(month)]} {int(year)}.")
    selected = st.session_state.get("last_generated")
    if selected:
        yy, mm = selected
        if (yy, mm) == (int(year), int(month)):
            roster = get_df("""
                SELECT r.work_date AS date, e.name AS employee, b.name AS brand,
                       p.name AS process, r.status, r.note
                FROM roster r
                JOIN employees e ON e.id=r.employee_id
                JOIN brands b ON b.id=r.brand_id
                JOIN processes p ON p.id=r.process_id
                WHERE substr(r.work_date,1,7)=?
                ORDER BY r.work_date, b.name, p.name
            """, (f"{yy:04d}-{mm:02d}",))
            st.markdown("#### Generated schedule")
            if not roster.empty:
                st.dataframe(roster, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download roster CSV", roster.to_csv(index=False).encode("utf-8"),
                    file_name=f"roster_{yy}_{mm:02d}.csv", mime="text/csv"
                )
            else:
                st.warning("No roster rows were generated. Check that active brands have active processes and assignments.")
            st.markdown("#### Validation results")
            issues = st.session_state.get("last_issues", [])
            if issues:
                st.warning(f"{len(issues)} issue(s) need attention.")
                st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
            else:
                st.success("No coverage gaps were detected for the configured rules.")

elif page == "Roster views":
    st.subheader("Roster explorer")
    month_value = st.date_input("Choose any date in the month", value=date.today())
    month_key = month_value.strftime("%Y-%m")
    view = st.selectbox("View by", ["Company", "Pod", "Brand", "Process", "Employee"])
    filters = {
        "Company": ("", ""),
        "Pod": ("JOIN pods pod ON pod.id=e.pod_id", "pod.name AS pod"),
        "Brand": ("", "b.name AS brand"),
        "Process": ("", "p.name AS process"),
        "Employee": ("", "e.name AS employee"),
    }
    join, _ = filters[view]
    query = """
        SELECT r.work_date AS date, e.name AS employee, pod.name AS pod,
               b.name AS brand, p.name AS process, r.status, r.note
        FROM roster r
        JOIN employees e ON e.id=r.employee_id
        JOIN pods pod ON pod.id=e.pod_id
        JOIN brands b ON b.id=r.brand_id
        JOIN processes p ON p.id=r.process_id
        WHERE substr(r.work_date,1,7)=?
        ORDER BY r.work_date, pod.name, b.name, p.name
    """
    df = get_df(query, (month_key,))
    if view != "Company" and not df.empty:
        column = {"Pod":"pod", "Brand":"brand", "Process":"process", "Employee":"employee"}[view]
        values = ["All"] + sorted(df[column].dropna().unique().tolist())
        selected = st.selectbox(f"Filter {view.lower()}", values)
        if selected != "All":
            df = df[df[column] == selected]
    if df.empty:
        st.info("No roster is saved for this month yet. Generate one first.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Export this view as CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"{view.lower()}_roster_{month_key}.csv", mime="text/csv")

elif page == "Manage data":
    st.subheader("Manage team, brands, processes, and assignments")
    tabs = st.tabs(["Employees", "Pods", "Brands", "Processes", "Assignments"])
    with tabs[0]:
        st.markdown("##### Current employees")
        st.dataframe(get_df("""
            SELECT e.id, e.name, e.email, p.name AS pod, e.weekly_off, e.active
            FROM employees e LEFT JOIN pods p ON p.id=e.pod_id ORDER BY e.name
        """), use_container_width=True, hide_index=True)
        with st.form("add_employee_form", clear_on_submit=True):
            st.markdown("##### Add employee")
            name = st.text_input("Full name")
            email = st.text_input("Email (optional)")
            pods = get_df("SELECT id, name FROM pods ORDER BY name")
            pod_choice = st.selectbox("Pod", pods["name"].tolist() if not pods.empty else ["No pod"])
            weekly_off = st.selectbox("Weekly off", ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
            submitted = st.form_submit_button("Add employee")
            if submitted:
                if not name.strip():
                    st.error("Enter an employee name.")
                else:
                    pod_id = int(pods.loc[pods["name"] == pod_choice, "id"].iloc[0]) if not pods.empty else None
                    add_employee(name.strip(), email.strip(), pod_id, weekly_off)
                    st.success("Employee added.")
                    st.rerun()
    with tabs[1]:
        st.dataframe(get_df("SELECT p.id, p.name, e.name AS pod_lead FROM pods p LEFT JOIN employees e ON e.id=p.lead_employee_id ORDER BY p.name"),
                     use_container_width=True, hide_index=True)
        with st.form("add_pod_form", clear_on_submit=True):
            name = st.text_input("New pod name")
            if st.form_submit_button("Add pod"):
                if name.strip():
                    add_pod(name.strip())
                    st.success("Pod added.")
                    st.rerun()
                else:
                    st.error("Enter a pod name.")
    with tabs[2]:
        st.dataframe(get_df("SELECT id, name, operating_rule, active FROM brands ORDER BY name"),
                     use_container_width=True, hide_index=True)
        with st.form("add_brand_form", clear_on_submit=True):
            name = st.text_input("Brand name")
            rule = st.selectbox("Default operating rule", ["365_days", "no_public_holidays", "sundays_and_holidays_off"])
            if st.form_submit_button("Add brand"):
                if name.strip():
                    add_brand(name.strip(), rule)
                    st.success("Brand added.")
                    st.rerun()
                else:
                    st.error("Enter a brand name.")
    with tabs[3]:
        st.dataframe(get_df("SELECT id, name, description, active FROM processes ORDER BY name"),
                     use_container_width=True, hide_index=True)
        with st.form("add_process_form", clear_on_submit=True):
            name = st.text_input("Process name")
            description = st.text_input("Description (optional)")
            if st.form_submit_button("Add process"):
                if name.strip():
                    add_process(name.strip(), description.strip())
                    st.success("Process added.")
                    st.rerun()
                else:
                    st.error("Enter a process name.")
    with tabs[4]:
        st.dataframe(get_df("""
            SELECT a.id, e.name AS employee, b.name AS brand, p.name AS process,
                   a.min_staff, a.active
            FROM assignments a JOIN employees e ON e.id=a.employee_id
            JOIN brands b ON b.id=a.brand_id JOIN processes p ON p.id=a.process_id
            ORDER BY b.name, p.name, e.name
        """), use_container_width=True, hide_index=True)
        with st.form("add_assignment_form", clear_on_submit=True):
            employees = get_df("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
            brands = get_df("SELECT id, name FROM brands WHERE active=1 ORDER BY name")
            processes = get_df("SELECT id, name FROM processes WHERE active=1 ORDER BY name")
            en = st.selectbox("Employee", employees["name"].tolist())
            bn = st.selectbox("Brand", brands["name"].tolist())
            pn = st.selectbox("Process", processes["name"].tolist())
            min_staff = st.number_input("Minimum staff needed for this brand/process/day", min_value=1, max_value=20, value=1)
            if st.form_submit_button("Add assignment"):
                eid = int(employees.loc[employees.name == en, "id"].iloc[0])
                bid = int(brands.loc[brands.name == bn, "id"].iloc[0])
                pid = int(processes.loc[processes.name == pn, "id"].iloc[0])
                try:
                    add_assignment(eid, bid, pid, int(min_staff))
                    st.success("Assignment added.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not add assignment: {exc}")

elif page == "Availability & holidays":
    st.subheader("Employee availability and public holidays")
    tab1, tab2 = st.tabs(["Employee availability", "Public holidays"])
    with tab1:
        st.caption("Add approved leave or comp-off to test how the roster changes.")
        employees = get_df("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        if not employees.empty:
            with st.form("availability_form", clear_on_submit=True):
                employee_name = st.selectbox("Employee", employees["name"].tolist())
                day = st.date_input("Unavailable date", value=date.today())
                kind = st.selectbox("Type", ["leave", "comp_off", "unavailable"])
                reason = st.text_input("Reason (optional)", value="Approved absence")
                if st.form_submit_button("Save unavailability"):
                    eid = int(employees.loc[employees.name == employee_name, "id"].iloc[0])
                    set_availability(eid, day.isoformat(), kind, reason.strip())
                    st.success("Availability saved. Regenerate the month to revalidate coverage.")
                    st.rerun()
        st.markdown("##### Saved availability")
        st.dataframe(get_df("""
            SELECT e.name AS employee, a.day, a.kind, a.reason
            FROM availability a JOIN employees e ON e.id=a.employee_id
            ORDER BY a.day DESC, e.name
        """), use_container_width=True, hide_index=True)
    with tab2:
        with st.form("holiday_form", clear_on_submit=True):
            hdate = st.date_input("Holiday date", value=date.today(), key="holiday_date")
            hname = st.text_input("Holiday name")
            if st.form_submit_button("Add public holiday"):
                if hname.strip():
                    add_holiday(hdate.isoformat(), hname.strip())
                    st.success("Holiday added. Regenerate the month to apply it.")
                    st.rerun()
                else:
                    st.error("Enter a holiday name.")
        st.dataframe(get_df("SELECT day, name FROM holidays ORDER BY day DESC"),
                     use_container_width=True, hide_index=True)

else:
    st.subheader("How this starter application works")
    st.markdown("""
    **Data model**
    - Employees belong to operational pods.
    - Assignments connect an employee to a brand and process.
    - Brand operating rules and process coverage requirements are stored separately from employee weekly offs.
    - Availability and public holidays are stored as dated records.

    **Scheduling**
    - The scheduler iterates over each day in the selected month and each active brand/process.
    - It finds assigned employees who are active and available, respects operating calendars and weekly offs, and avoids assigning one employee to multiple roster rows on the same date.
    - It records a coverage issue if the number of available employees is below the configured minimum.
    - A final validation pass checks saved assignments against coverage requirements.

    **Assumptions and limitations**
    - This starter uses a deterministic greedy approach, not a mathematical optimizer.
    - Each employee can be assigned to at most one brand/process row per day. Real shifts and time-of-day overlap are not yet modeled.
    - Public holidays are global. Client-specific holiday calendars can be added as an extension.
    - Weekly offs are one fixed weekday per employee.
    - Managers should review warnings before treating a roster as publishable.
    """)
    st.info("The assessment prioritizes reliable scheduling and clear conflict detection over a visually impressive interface. Test edge cases before submission.")
