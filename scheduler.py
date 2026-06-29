import calendar
from datetime import date
import random
from database import get_df

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _operates(rule, day, is_holiday):
    weekday = day.strftime("%A")
    if rule == "365_days":
        return True
    if rule == "no_public_holidays":
        return not is_holiday
    if rule == "sundays_and_holidays_off":
        return weekday != "Sunday" and not is_holiday
    return True

def generate_roster(year, month):
    employees = get_df("SELECT id, name, weekly_off, active FROM employees WHERE active=1")
    brands = get_df("SELECT id, name, operating_rule FROM brands WHERE active=1")
    processes = get_df("SELECT id, name FROM processes WHERE active=1")
    
    assignments = get_df("""
        SELECT a.id, a.employee_id, a.brand_id, a.process_id, a.min_staff,
               e.name AS employee_name, e.weekly_off, b.name AS brand_name,
               b.operating_rule, p.name AS process_name
        FROM assignments a
        JOIN employees e ON e.id=a.employee_id
        JOIN brands b ON b.id=a.brand_id
        JOIN processes p ON p.id=a.process_id
        WHERE a.active=1 AND e.active=1 AND b.active=1 AND p.active=1
        ORDER BY b.name, p.name, e.name
    """)
    
    availability_df = get_df("SELECT employee_id, day, kind, reason FROM availability")
    holidays_df = get_df("SELECT day, name FROM holidays")
    
    unavailable = {(int(r.employee_id), r.day): (r.kind, r.reason or "") for r in availability_df.itertuples()}
    holidays = {r.day: r.name for r in holidays_df.itertuples()}
    
    if assignments.empty:
        return [], [{"date": f"{year:04d}-{month:02d}", "brand": "-", "process": "-",
                     "required": "-", "available": 0, "issue": "No active assignments configured."}]
                     
    rows, issues = [], []
    days_in_month = calendar.monthrange(year, month)[1]
    used_by_date = {}
    
    
    emp_work_counts = {int(eid): 0 for eid in employees["id"]}
    
    
    requirements = assignments.groupby(["brand_id", "process_id"], as_index=False)["min_staff"].max()
    
    for day_num in range(1, days_in_month + 1):
        day = date(year, month, day_num)
        day_s = day.isoformat()
        holiday_name = holidays.get(day_s)
        used = used_by_date.setdefault(day_s, set())
        
        for req in requirements.itertuples():
            bid, pid, min_staff = int(req.brand_id), int(req.process_id), int(req.min_staff)
            candidates = assignments[(assignments.brand_id == bid) & (assignments.process_id == pid)]
            
            if candidates.empty:
                continue
                
            sample = candidates.iloc[0]
            if not _operates(sample["operating_rule"], day, bool(holiday_name)):
                continue
                
            eligible = []
            blocked_reasons = []
            
            for row in candidates.itertuples():
                eid = int(row.employee_id)
                if eid in used:
                    blocked_reasons.append(f"{row.employee_name} already working elsewhere today")
                    continue
                if row.weekly_off == day.strftime("%A"):
                    blocked_reasons.append(f"{row.employee_name} has weekly off ({row.weekly_off})")
                    continue
                absence = unavailable.get((eid, day_s))
                if absence:
                    blocked_reasons.append(f"{row.employee_name} unavailable ({absence[0]})")
                    continue
                eligible.append(row)
            
            
            eligible.sort(key=lambda x: emp_work_counts.get(int(x.employee_id), 0))
            
            chosen = eligible[:min_staff]
            for person in chosen:
                rows.append({
                    "work_date": day_s, "employee_id": int(person.employee_id),
                    "brand_id": bid, "process_id": pid, "status": "Working", "note": ""
                })
                used.add(int(person.employee_id))
                emp_work_counts[int(person.employee_id)] += 1
                
            if len(chosen) < min_staff:
                issues.append({
                    "date": day_s, "brand": sample["brand_name"], "process": sample["process_name"],
                    "required": min_staff, "available": len(chosen),
                    "issue": "Staff Shortage. " + ("; ".join(blocked_reasons) if blocked_reasons else "Reconfigure staff allocations.")
                })
                
    return rows, issues

def validate_roster(year, month):
    rows, issues = generate_roster(year, month)
    return issues
