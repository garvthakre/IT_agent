"""
demo.py — Interactive Demo Runner
===================================
Runs preset IT tasks one by one for the Loom recording.
Each task pauses between runs so you can narrate.

Usage:
    python demo.py
"""

import asyncio
import sys
import os

# Make sure agent module is importable
sys.path.insert(0, os.path.dirname(__file__))
from agent import run_it_task

# ── Demo tasks ────────────────────────────────────────────────────────────────

DEMO_TASKS = [
    {
        "title": "Task 1 — Reset Password",
        "task": "Reset the password for john@company.com",
        "description": "Finds John Smith in the user list and resets his password",
    },
    {
        "title": "Task 2 — Create New User",
        "task": "Create a new employee account. Full name: garv Thakre, email: garvthakre@gmail.com, role: employee",
        "description": "Fills out the create user form and submits it",
    },
    {
        "title": "Task 3 — Disable Account",
        "task": "Disable the account for garvthakre@gmail.com",
        "description": "Finds garv Thakre and disables his account",
    },
    {
        "title": "Task 4 — Conditional (Bonus)",
        "task": (
            "Check if charlie@company.com exists in the system. "
            "If the user does not exist, create them as an employee with the name Charlie Brown. "
            "After creating or finding them, disable their account."
        ),
        "description": "Multi-step: check existence → create if missing → disable account",
    },
]


async def run_demo():
    print("\n" + "="*60)
    print("  IT SUPPORT AI AGENT — DEMO")
    print("="*60)
    print("Make sure the admin panel is running at http://localhost:5000")
    print("="*60 + "\n")

    for i, demo in enumerate(DEMO_TASKS):
        print(f"\n[{i+1}/{len(DEMO_TASKS)}] {demo['title']}")
        print(f"     {demo['description']}")

        if i > 0:
            try:
                input("\nPress ENTER to run this task (or Ctrl+C to stop)... ")
            except EOFError:
                pass

        await run_it_task(demo["task"])

        if i < len(DEMO_TASKS) - 1:
            print("\n✓ Task complete. Next task ready.")

    print("\n" + "="*60)
    print("  ALL DEMO TASKS COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
