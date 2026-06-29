# Datastaw Smart Roster Management System

A Python + Streamlit starter application for the Datastaw AI + Tech Internship assessment.

## Features in this starter

- SQLite database with employees, pods, brands, processes, assignments, availability, holidays, and roster records.
- Seeded fictional sample data with 30 employees, 10 brands, four pods, and multiple processes.
- Add employees, pods, brands, processes, and employee-brand-process assignments through the UI.
- Configure fixed weekly offs, dated leave/comp-off/unavailability, and public holidays.
- Generate a monthly roster.
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

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, run this instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`. Open it in your browser.

## Database

The application creates `roster.db` automatically the first time it starts. Demo data is seeded if the employee table is empty. The database file is ignored by Git so local data is not accidentally committed.

To reset demo data, stop the app and delete `roster.db`; then restart the app.

## Scheduling approach

The starter uses a deterministic greedy scheduler. For every date in the selected month, it checks each active brand/process requirement, determines whether that process operates that day, excludes employees who are inactive, on their fixed weekly off, unavailable, or already assigned to another roster row that day, then assigns enough people to meet the minimum coverage requirement. If it cannot meet the requirement, it records a coverage gap with a reason.

The approach is deliberately transparent and easy to explain. It is not an optimization solver and may report gaps that a more sophisticated global scheduler could avoid by choosing a different assignment order.

## Data-model notes

- `employees` stores employee profile, pod, active flag, and weekly off.
- `pods` stores pod names and a lead employee.
- `brands` stores client operating rules.
- `processes` stores operational work types.
- `assignments` is the relationship table connecting employees to brand/process combinations and minimum coverage.
- `availability` stores dated leave, comp-off, and unavailability.
- `holidays` stores global public holidays.
- `roster` stores generated employee assignments for dates.

## Assumptions and known limitations

- The seeded brand/employee names are fictional.
- The sample contains 30 employees, 10 brands, four pods, and four processes.
- A brand's operating rule is applied to all processes under that brand. A production-ready extension should support rules at brand-process level.
- Holidays are global; client-specific holiday calendars are not implemented.
- Employees have one fixed weekly-off weekday. Rotating or multiple weekly offs are not yet supported.
- One employee can be assigned to only one brand/process row per date. Shift start/end times are not modeled.
- `min_staff` is stored per assignment; the scheduler uses the maximum value among assignments for each brand/process as the minimum required coverage.
- The app does not implement authentication, roster approval, or edit-in-place for generated roster cells yet.
- Review all warnings and test edge cases before publishing a roster.

## Assessment README questions

1. **How did you model entities and relationships?**  
   Employees, pods, brands, and processes are separate entities. The assignments table models the many-to-many relationship between employees and brand/process combinations. Availability and holidays are dated tables, while roster rows store generated assignments.

2. **How does roster generation work?**  
   A deterministic greedy scheduler loops through dates and brand/process requirements. It filters assigned employees by operating calendar, weekly off, availability, and daily double-booking, then assigns the minimum required staff and reports coverage gaps.

3. **How are single-resource and multi-resource brands handled?**  
   Both use the same assignments table. A single-resource brand has one employee assigned to its processes; a multi-resource brand has multiple employee assignments, potentially across different processes.

4. **What if the only employee for a brand is unavailable?**  
   The scheduler excludes that employee and reports a coverage gap with the date, brand, process, required staff, available staff, and blocking reason. A manager can add or change an assignment and regenerate the month.

5. **How are conflicts and insufficient staffing handled?**  
   The scheduler avoids assigning one employee to more than one roster row on the same date and reports when eligible staffing falls below the minimum. The current version does not model time-of-day shift overlaps.

6. **What is automated versus human-controlled?**  
   Roster generation and basic validation are automated. The manager controls employee assignments, leave input, operating rules, and decisions about resolving unfilled coverage.

7. **What would change if the company doubled in size?**  
   I would consider PostgreSQL, database indexes, stronger data validation, more efficient scheduling, background generation for large rosters, and automated tests. I would also consider an optimization solver to improve global coverage.

8. **What would I improve with one more week?**  
   I would add process-specific calendars, configurable rotating weekly offs, shift times, a stronger global constraint solver, edit-and-revalidate workflows, authentication, approval/publishing, and automated tests.

## Deployment

A straightforward option is Streamlit Community Cloud:
1. Push this project to a GitHub repository.
2. Open Streamlit Community Cloud and connect the repository.
3. Set the main file path to `app.py`.
4. Deploy and test the public URL.

Important: local SQLite data is ephemeral on many hosted environments. For persistent deployed data, use a managed PostgreSQL database and configure credentials through deployment secrets. Do not commit secrets or real employee data.

## Before submission

- Test all three operating rules.
- Test a sole employee's absence and verify a coverage gap is shown.
- Test an employee assigned to two processes on the same date.
- Test public holidays and weekly offs.
- Test a month with no assignments.
- Record a 3–5 minute demo.
- Include the public app URL, GitHub repository, LinkedIn profile, and a 2–3 sentence approach note in the submission email.
