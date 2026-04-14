"""
agent.py — IT Support AI Agent
================================
Uses browser-use to control the IT Admin Panel at localhost:5000.
The agent sees the page like a human, clicks buttons, fills forms,
and reads results — no direct API calls or DOM shortcuts.

Supports multiple AI providers (set AI_PROVIDER in .env):
    groq      — free, fast (llama-3.3-70b-versatile) ← default
    anthropic — Claude claude-opus-4-5 (paid)

Usage:
    python agent.py "reset password for john@company.com"
    python agent.py "create a new employee account for Jane Doe, email jane@company.com"
    python agent.py "disable mike@company.com"
    python agent.py "check if sarah@company.com exists, if not create them, then disable their account"

Requirements:
    pip install -r requirements.txt
    playwright install chromium
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# ── Provider config (mirrors Nexus pattern exactly) ───────────────────────────

AI_PROVIDER   = os.getenv("AI_PROVIDER", "groq").lower()

GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")

ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "http://localhost:5000")

# ── Validate env ──────────────────────────────────────────────────────────────

def validate_env():
    required = {
        "groq":      ("GROQ_API_KEY",      GROQ_API_KEY),
        "anthropic": ("ANTHROPIC_API_KEY",  ANTHROPIC_API_KEY),
    }

    if AI_PROVIDER not in required:
        print(f"\n  Unknown AI_PROVIDER '{AI_PROVIDER}'. Must be: groq | anthropic")
        sys.exit(1)

    env_name, env_val = required[AI_PROVIDER]
    if not env_val or env_val.startswith("your_"):
        print(f"\n  {env_name} not set.")
        print(f"    Add it to agent/.env:")
        print(f"    {env_name}=your_key_here\n")
        sys.exit(1)

    print(f"✓ Provider: {AI_PROVIDER.upper()} — model: {GROQ_MODEL if AI_PROVIDER == 'groq' else ANTHROPIC_MODEL}")

validate_env()

# ── Imports (after env check) ─────────────────────────────────────────────────

from browser_use import Agent, BrowserConfig

# ── LLM factory (same pattern as Nexus planner.ts) ───────────────────────────

def get_llm():
    """Return the correct LangChain LLM based on AI_PROVIDER."""

    if AI_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
            temperature=0.0,
            max_tokens=4096,
        )

    if AI_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=ANTHROPIC_MODEL,
            anthropic_api_key=ANTHROPIC_API_KEY,
            temperature=0.0,
            max_tokens=4096,
        )

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are an IT support agent with access to a company IT admin panel.

ADMIN PANEL URL: {ADMIN_PANEL_URL}

PANEL STRUCTURE:
- Dashboard ({ADMIN_PANEL_URL}/) — shows user stats and quick links
- User List ({ADMIN_PANEL_URL}/users) — table of all users with action buttons
- Create User ({ADMIN_PANEL_URL}/create-user) — form to add a new user

USER LIST PAGE:
- Each row shows: Name, Email, Role, Status (active/disabled), Created date
- Action buttons per row: "Reset Password", "Disable" (or "Enable"), "Delete"
- There is a search box at the top — use it to find specific users by name or email

AVAILABLE ACTIONS:
1. Reset Password — click "Reset Password" next to a user, then confirm by clicking "Yes, Reset Password"
2. Disable/Enable Account — click "Disable" or "Enable" button next to a user
3. Create User — go to /create-user, fill Name + Email + Role, click "Create User"
4. Delete User — click "Delete" next to a user
5. Search for user — use the search box on /users page

IMPORTANT RULES:
- Always start by navigating to {ADMIN_PANEL_URL}
- To find a specific user, go to /users and use the search box with their email or name
- After completing an action, read the confirmation page and report what it says
- For conditional tasks (e.g. "check if X exists, if not create them"), search first,
  check if results appear in the table, then decide what to do next
- Always report the outcome clearly including any generated passwords

After every task, clearly state:
1. What action you performed
2. Who it was performed on (name + email)
3. The result (including temporary password if one was generated)
"""

# ── Agent runner ──────────────────────────────────────────────────────────────

async def run_it_task(task: str) -> str:
    """Run an IT support task using the browser agent."""

    print(f"\n{'='*60}")
    print(f"IT AGENT — {AI_PROVIDER.upper()}")
    print(f"{'='*60}")
    print(f"Task:  {task}")
    print(f"Panel: {ADMIN_PANEL_URL}")
    print(f"{'='*60}\n")

    llm = get_llm()

    agent = Agent(
        task=f"{SYSTEM_PROMPT}\n\nIT TASK TO COMPLETE:\n{task}",
        llm=llm,
        browser_config=BrowserConfig(
            headless=False,   # show browser window for demo/Loom recording
        ),
        max_failures=3,
        retry_delay=2,
    )

    try:
        result = await agent.run(max_steps=25)

        print(f"\n{'='*60}")
        print("AGENT RESULT")
        print(f"{'='*60}")
        print(result)
        print(f"{'='*60}\n")

        return str(result)

    except Exception as e:
        error_msg = f"Agent failed: {e}"
        print(f"\n  {error_msg}\n")
        return error_msg


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"\nCurrent provider: {AI_PROVIDER.upper()} ({GROQ_MODEL if AI_PROVIDER == 'groq' else ANTHROPIC_MODEL})")
        print("\nUsage:")
        print('  python agent.py "reset password for john@company.com"')
        print('  python agent.py "create a new employee Jane Doe, email jane@company.com"')
        print('  python agent.py "disable the account for mike@company.com"')
        print('  python agent.py "check if sarah@company.com exists, if not create her, then disable the account"')
        print("\nSwitch provider:")
        print('  AI_PROVIDER=groq      python agent.py "..."   # free, fast')
        print('  AI_PROVIDER=anthropic python agent.py "..."   # Claude\n')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    asyncio.run(run_it_task(task))


if __name__ == "__main__":
    main()
