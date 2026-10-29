# Datastaw Smart Roster Management System

A Python + Streamlit application for the Datastaw AI + Tech Internship assessment.

## Features in this implementation

- SQLite database with employees, pods, brands, processes, assignments, availability, holidays, and roster records.
- Balanced fictional sample data with 30 employees, 10 brands, four pods, and multiple processes.
- Add employees, pods, brands, processes, and employee-brand-process assignments through the UI.
- Configure fixed weekly offs, dated leave/comp-off/unavailability, and public holidays.
- Generate a monthly roster with a fair work-distribution engine.
- Detect insufficient coverage and explain the blocked candidates.
- View rosters by company, pod, brand, process, or employee.
- Export roster views to CSV.

## Requirements

- Python 3.10 or newer recommended
- VS Code
- Internet access to install Python packages and deploy the app

## Run locally in VS Code

Open this folder in VS Code, then open its terminal.

### Windows PowerShell

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py

If PowerShell blocks activation, run this instead:

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py

### macOS / Linux

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py

Streamlit will print a local URL, usually http://localhost:8501. Open it in your browser.

## Database

The application creates roster.db automatically the first time it starts. Demo data is seeded if the employee table is empty. The database file is ignored by Git so local data is not accidentally committed.

To reset demo data, stop the app and delete roster.db; then restart the app.

## Scheduling approach

The system incorporates a load-balanced rotation engine alongside the deterministic scheduler. For every date in the selected month, it checks each active brand/process requirement, determines whether that process operates that day, and excludes employees who are inactive, on their fixed weekly off, unavailable, or already assigned to another roster row that day. 

To ensure fairness and prevent resource burnout, the engine tracks cumulative monthly work counts and prioritizes unassigned eligible team members who have worked the fewest days. If it cannot meet the requirement, it records a coverage gap with a transparent reason.

## Data-model notes

- employees stores employee profile, pod, active flag, and weekly off.
- pods stores pod names and a lead employee.
- brands stores client operating rules.
- processes stores operational work types.
- assignments models relationships connecting employees to brand/process combinations and minimum coverage.
- availability stores dated leave, comp-off, and unavailability.
- holidays stores global public holidays.
- roster stores generated employee assignments for dates.

## Assumptions and known limitations

- The seeded brand/employee names are fictional.
- A brand's operating rule is applied to all processes under that brand.
- Holidays are global; client-specific holiday calendars are not implemented.
- Employees have one fixed weekly-off weekday. Rotating weekly offs are not yet supported.
- One employee can be assigned to only one brand/process row per date. Shift start/end times are not modeled.
- min_staff is stored per assignment; the scheduler uses the maximum value among assignments for each brand/process as the minimum required coverage.
- The app does not implement authentication, roster approval, or edit-in-place for generated roster cells yet.

## Assessment README questions

1. How did you model entities and relationships?
   Employees, pods, brands, and processes are separate relational tables. The assignments table models the many-to-many relationship between employees and brand/process combinations using foreign keys and composite unique constraints to guarantee structural data integrity.

2. How does roster generation work?
   The scheduler loops through month dates and brand/process requirements. It filters assigned employees by operating calendar, weekly off, availability, and daily double-booking protections, then assigns staff using a dynamic work-count rotation matrix to maintain scheduling fairness across the team.

3. How are single-resource and multi-resource brands handled?
   Both use the same underlying relational assignments schema. A single-resource brand maps its dedicated employee to the primary process, while a multi-resource brand associates multiple employee rows across overlapping process configurations.

4. What if the only employee for a brand is unavailable?
   The scheduler excludes that employee and logs a transparent coverage gap detailing the target date, brand, process, required staff, available staff, and blocking reason so a manager can handle adjustments manually.

5. How are conflicts and insufficient staffing handled?
   The engine avoids assigning one resource to more than one roster row on the same date and prints specific validation errors when eligible availability drops below the required min_staff. It isolates validations without breaking the thread execution.

6. What is automated versus human-controlled?
   The complex scheduling logic, double-booking calculations, and rule validations are automated. The operational boundaries—such as team onboarding, customized assignments, and managing leaf configurations—remain under human control.

7. What would change if the company doubled in size?
   I would migrate the relational backend to PostgreSQL, add specific database indexes on date columns, implement background worker processes for scheduling tasks, incorporate comprehensive unit tests, and leverage global optimization solvers.

8. What would I improve with one more week?
   I would add process-specific operating calendars, granular shift timings, configurable rotating weekly off patterns, authentication setups, role-based workflows for roster publishing approvals, and interactive cell-editing inside the UI view.
