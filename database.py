import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).with_name("roster.db")

def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def run(sql, params=()):
    with connect() as con:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid

def execute(sql, params=()):
    with connect() as con:
        con.executescript(sql)
        con.commit()

def get_df(sql, params=()):
    with connect() as con:
        return pd.read_sql_query(sql, con, params=params)

def scalar(sql, params=()):
    with connect() as con:
        row = con.execute(sql, params).fetchone()
        return row[0] if row else 0

def init_db():
    execute("""
    CREATE TABLE IF NOT EXISTS pods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        lead_employee_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        pod_id INTEGER REFERENCES pods(id),
        weekly_off TEXT NOT NULL DEFAULT 'Sunday',
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        operating_rule TEXT NOT NULL DEFAULT '365_days',
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS processes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        brand_id INTEGER NOT NULL REFERENCES brands(id),
        process_id INTEGER NOT NULL REFERENCES processes(id),
        min_staff INTEGER NOT NULL DEFAULT 1,
        active INTEGER NOT NULL DEFAULT 1,
        UNIQUE(employee_id, brand_id, process_id)
    );
    CREATE TABLE IF NOT EXISTS availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        day TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('leave','comp_off','unavailable')),
        reason TEXT,
        UNIQUE(employee_id, day)
    );
    CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS roster (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_date TEXT NOT NULL,
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        brand_id INTEGER NOT NULL REFERENCES brands(id),
        process_id INTEGER NOT NULL REFERENCES processes(id),
        status TEXT NOT NULL DEFAULT 'Working',
        note TEXT,
        UNIQUE(work_date, employee_id, brand_id, process_id)
    );
    """)

def seed_demo_data():
    pods = ["Alpha Pod", "Beta Pod", "Gamma Pod", "Delta Pod"]
    for pod in pods:
        run("INSERT OR IGNORE INTO pods(name) VALUES (?)", (pod,))
        
    processes = [
        ("Customer Support", "Customer queries and service"),
        ("Abandoned Cart Conversions", "Recover abandoned carts"),
        ("Retention", "Customer retention operations"),
        ("NDR Management", "Non-delivery report management"),
    ]
    for name, desc in processes:
        run("INSERT OR IGNORE INTO processes(name, description) VALUES (?,?)", (name, desc))
        
    brands = [
        ("StyleKart", "365_days"), ("GlowHouse", "no_public_holidays"),
        ("UrbanNest", "sundays_and_holidays_off"), ("FitFuel", "365_days"),
        ("PetPlanet", "no_public_holidays"), ("HomeHarbor", "sundays_and_holidays_off"),
        ("DailyNeeds", "365_days"), ("PureSkin", "no_public_holidays"),
        ("TechTrove", "sundays_and_holidays_off"), ("BabyBloom", "365_days"),
    ]
    for name, rule in brands:
        run("INSERT OR IGNORE INTO brands(name, operating_rule) VALUES (?,?)", (name, rule))
        
    pod_rows = get_df("SELECT id, name FROM pods")
    pod_ids = {r["name"]: int(r["id"]) for _, r in pod_rows.iterrows()}
    
    employee_names = [
        "Aarav Shah","Aditi Patil","Arjun Mehta","Ananya Rao","Vivaan Joshi",
        "Isha Kulkarni","Reyansh Singh","Saanvi Desai","Advik Nair","Myra Gupta",
        "Krish Verma","Sara Khan","Atharv Pawar","Diya Iyer","Kabir Jain",
        "Anvi More","Rudra Bhosale","Kiara Shah","Ishaan Kapoor","Riya Naik",
        "Dhruv Mishra","Pari Chavan","Neil Thomas","Tara Menon","Omkar Jadhav",
        "Mira Sane","Yash Malhotra","Zoya Sheikh","Samar Kulkarni","Avni Joshi"
    ]
    
    weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for i, name in enumerate(employee_names):
        pod_name = pods[i % len(pods)]
        run("""INSERT OR IGNORE INTO employees(name,email,pod_id,weekly_off)
               VALUES (?,?,?,?)""",
            (name, f"employee{i+1:02d}@example.com", pod_ids[pod_name], weekdays[i % 7]))
            
    emp_rows = get_df("SELECT id, name FROM employees ORDER BY id")
    brand_rows = get_df("SELECT id, name FROM brands ORDER BY id")
    proc_rows = get_df("SELECT id, name FROM processes ORDER BY id")
    
    eids = {r["name"]: int(r["id"]) for _, r in emp_rows.iterrows()}
    bids = {r["name"]: int(r["id"]) for _, r in brand_rows.iterrows()}
    pids = {r["name"]: int(r["id"]) for _, r in proc_rows.iterrows()}
    
    brand_list = [b["name"] for _, b in brand_rows.iterrows()]
    process_list = [p["name"] for _, p in proc_rows.iterrows()]
    
    for i, brand_name in enumerate(brand_list[:8]):
        emp = employee_names[i]
        run("INSERT OR IGNORE INTO assignments(employee_id,brand_id,process_id,min_staff) VALUES (?,?,?,1)",
            (eids[emp], bids[brand_name], pids["Customer Support"]))
            
    multi_brands = [(brand_list[8], 8), (brand_list[9], 12)]
    for brand_name, start in multi_brands:
        for j in range(4):
            if start+j < len(employee_names):
                emp = employee_names[start+j]
                proc = process_list[j % len(process_list)]
                run("INSERT OR IGNORE INTO assignments(employee_id,brand_id,process_id,min_staff) VALUES (?,?,?,1)",
                    (eids[emp], bids[brand_name], pids[proc]))
                
    for i in range(16, len(employee_names)):
        b_name = brand_list[i % len(brand_list)]
        p_name = process_list[(i + 1) % len(process_list)]
        run("INSERT OR IGNORE INTO assignments(employee_id,brand_id,process_id,min_staff) VALUES (?,?,?,1)",
            (eids[employee_names[i]], bids[b_name], pids[p_name]))
            
    for pod_name in pods:
        lead = get_df("SELECT id FROM employees WHERE pod_id=? ORDER BY id LIMIT 1", (pod_ids[pod_name],))
        if not lead.empty:
            run("UPDATE pods SET lead_employee_id=? WHERE id=?", (int(lead.iloc[0]["id"]), pod_ids[pod_name]))

def add_employee(name, email, pod_id, weekly_off):
    return run("INSERT INTO employees(name,email,pod_id,weekly_off) VALUES (?,?,?,?)",
               (name, email or None, pod_id, weekly_off))

def add_pod(name):
    return run("INSERT INTO pods(name) VALUES (?)", (name,))

def add_brand(name, operating_rule):
    return run("INSERT INTO brands(name,operating_rule) VALUES (?,?)", (name, operating_rule))

def add_process(name, description):
    return run("INSERT INTO processes(name,description) VALUES (?,?)", (name, description or None))

def add_assignment(employee_id, brand_id, process_id, min_staff):
    return run("""INSERT INTO assignments(employee_id,brand_id,process_id,min_staff) 
                  VALUES (?,?,?,?)""", (employee_id, brand_id, process_id, min_staff))

def set_availability(employee_id, day, kind, reason):
    return run("""INSERT OR REPLACE INTO availability(employee_id, day, kind, reason) 
                  VALUES (?,?,?,?)""", (employee_id, day, kind, reason))

def add_holiday(day, name):
    return run("INSERT OR IGNORE INTO holidays(day, name) VALUES (?,?)", (day, name))

def clear_roster_month(year, month):
    month_str = f"{year:04d}-{month:02d}%"
    with connect() as con:
        con.execute("DELETE FROM roster WHERE work_date LIKE ?", (month_str,))
        con.commit()

def save_roster_rows(rows):
    if not rows:
        return
    with connect() as con:
        con.executemany("""
            INSERT OR IGNORE INTO roster (work_date, employee_id, brand_id, process_id, status, note)
            VALUES (:work_date, :employee_id, :brand_id, :process_id, :status, :note)
        """, rows)
        con.commit()
