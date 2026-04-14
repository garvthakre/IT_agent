import sqlite3
from datetime import datetime, timedelta
import random
import string
import os

DB_PATH = "database.db"


def generate_temp_password():
    chars = string.ascii_uppercase + string.digits
    return "TMP-" + "".join(random.choices(chars, k=8))


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT UNIQUE NOT NULL,
            role        TEXT NOT NULL DEFAULT 'employee',
            status      TEXT NOT NULL DEFAULT 'active',
            password    TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)

    seed_users = [
        ("John Smith",      "john@company.com",    "admin",    "active"),
        ("Sarah Connor",    "sarah@company.com",   "employee", "active"),
        ("Mike Johnson",    "mike@company.com",    "employee", "active"),
        ("Emily Davis",     "emily@company.com",   "viewer",   "active"),
        ("Robert Brown",    "robert@company.com",  "employee", "disabled"),
        ("Lisa Wilson",     "lisa@company.com",    "admin",    "active"),
        ("David Martinez",  "david@company.com",   "employee", "active"),
        ("Anna Taylor",     "anna@company.com",    "viewer",   "disabled"),
    ]

    base_date = datetime.now() - timedelta(days=30)

    for i, (name, email, role, status) in enumerate(seed_users):
        created = (base_date + timedelta(days=i * 4)).isoformat()
        password = generate_temp_password()
        c.execute(
            "INSERT INTO users (name, email, role, status, password, created_at) VALUES (?,?,?,?,?,?)",
            (name, email, role, status, password, created)
        )
        print(f"  + {name} ({email}) — {role} — {status}")

    conn.commit()
    conn.close()
    print(f"\nDatabase initialized at {DB_PATH} with {len(seed_users)} users.")


if __name__ == "__main__":
    init_db()
