"""
agent.py — IT Support AI Agent
================================
Uses direct Playwright to control the IT Admin Panel at 
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER   = os.getenv("AI_PROVIDER", "groq").lower()
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")
ADMIN_PANEL_URL = os.getenv("ADMIN_PANEL_URL", "http://localhost:5000")

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
        print(f"\n  {env_name} not set. Add it to agent/.env\n")
        sys.exit(1)
    print(f"✓ Provider: {AI_PROVIDER.upper()} — model: {GROQ_MODEL if AI_PROVIDER == 'groq' else ANTHROPIC_MODEL}")

validate_env()

def get_llm():
    if AI_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model=GROQ_MODEL,
            temperature=0.0,
            max_tokens=2048,  # keep it small — we only need one JSON object
        )
    if AI_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=ANTHROPIC_MODEL,
            anthropic_api_key=ANTHROPIC_API_KEY,
            temperature=0.0,
            max_tokens=512,
        )

# ── Agent runner ──────────────────────────────────────────────────────────────

async def run_it_task(task: str) -> str:
    from playwright.async_api import async_playwright
    import json

    print(f"\n{'='*60}")
    print(f"IT AGENT — {AI_PROVIDER.upper()}")
    print(f"{'='*60}")
    print(f"Task:  {task}")
    print(f"Panel: {ADMIN_PANEL_URL}")
    print(f"{'='*60}\n")

    llm = get_llm()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        async def navigate(url):
            await page.goto(url)
            await page.wait_for_load_state("networkidle")

        async def ask_llm(page_html: str, history: list) -> dict:
            history_text = "\n".join(history[-6:]) if history else "None yet"

            prompt = f"""You are controlling an IT ADMIN PANEL at {ADMIN_PANEL_URL}.

THIS IS AN ADMIN PANEL — NOT A USER-FACING WEBSITE.
- There is NO login page, NO forgot-password page, NO /login, NO /forgot-password.
- NEVER navigate to /login or /forgot-password — those do not exist.
- The only valid URLs are:
    {ADMIN_PANEL_URL}/          (dashboard)
    {ADMIN_PANEL_URL}/users     (user list with search box)
    {ADMIN_PANEL_URL}/create-user (form to add new user)
    {ADMIN_PANEL_URL}/reset-password/<id>  (reached by clicking button, not directly)

HOW TO COMPLETE TASKS:
- To reset a password: go to /users, search for the user, click "Reset Password" button in their row, then click "Yes, Reset Password"
- To disable an account: go to /users, search for the user, click "Disable" button in their row
- To create a user: go to /create-user, fill the form fields, click "Create User"
- To find a user: go to /users and type their email in the search box (input[name="search"]), then click Search

CURRENT PAGE HTML (first 2500 chars):
{page_html[:2500]}

RECENT ACTIONS TAKEN:
{history_text}

TASK TO COMPLETE: {task}

RULES:
- If you see a 404 page, you went to a wrong URL. Go to {ADMIN_PANEL_URL}/users instead.
- If you keep repeating the same action, try something different.
- If the task is complete (you see a confirmation page with ✅), respond with action=done.
- Read the page HTML carefully before deciding what to do.

Respond with ONLY valid JSON, no markdown, no explanation:
{{
  "action": "navigate" | "click" | "fill" | "done" | "failed",
  "url": "<full url — ONLY if action=navigate>",
  "selector": "<css selector — ONLY if action=click or fill>",
  "value": "<text to type — ONLY if action=fill>",
  "result": "<summary — ONLY if action=done or failed>"
}}"""

            response = llm.invoke(prompt)
            text = response.content.strip()
            # strip markdown fences if present
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        text = part
                        break
            return json.loads(text.strip())

        history = []
        result_summary = "No result"
        last_actions = []  # for loop detection

        try:
            await navigate(ADMIN_PANEL_URL + "/users")
            history.append(f"Started at {ADMIN_PANEL_URL}/users")

            for step in range(30):
                html = await page.content()
                print(f"  Step {step+1}...", end=" ", flush=True)

                try:
                    action = await ask_llm(html, history)
                except Exception as e:
                    print(f"LLM parse error: {e} — retrying with navigate to /users")
                    await navigate(ADMIN_PANEL_URL + "/users")
                    history.append("Parse error — reset to /users")
                    await asyncio.sleep(2)
                    continue

                action_str = f"{action.get('action')}:{action.get('url') or action.get('selector') or ''}"
                print(f"{action.get('action')} — {action.get('url') or action.get('selector') or action.get('result', '')}")

                # Loop detection — if same action 3 times in a row, break out
                last_actions.append(action_str)
                if len(last_actions) > 3 and len(set(last_actions[-3:])) == 1:
                    print(f"\n  ⚠ Loop detected on: {action_str} — forcing navigate to /users")
                    await navigate(ADMIN_PANEL_URL + "/users")
                    history.append(f"Loop detected — reset to /users")
                    last_actions = []
                    await asyncio.sleep(1)
                    continue

                # Block bad URLs
                url = action.get("url", "")
                if action["action"] == "navigate" and url and (
                    "/login" in url or "/forgot" in url or "/password-reset" in url
                    or not url.startswith(ADMIN_PANEL_URL)
                ):
                    print(f"  ⛔ Blocked bad URL: {url} — redirecting to /users")
                    await navigate(ADMIN_PANEL_URL + "/users")
                    history.append(f"Blocked bad URL {url} — went to /users")
                    await asyncio.sleep(1)
                    continue

                if action["action"] == "navigate":
                    await navigate(action["url"])
                    history.append(f"Navigated to {action['url']}")

                elif action["action"] == "click":
                    try:
                        await page.click(action["selector"], timeout=5000)
                        await page.wait_for_load_state("networkidle")
                        history.append(f"Clicked {action['selector']}")
                    except Exception as e:
                        print(f"  Click failed ({e}) — trying visible click")
                        try:
                            await page.locator(action["selector"]).first.click()
                            await page.wait_for_load_state("networkidle")
                            history.append(f"Clicked (locator) {action['selector']}")
                        except Exception as e2:
                            history.append(f"Click failed: {action['selector']} — {e2}")

                elif action["action"] == "fill":
                    try:
                        await page.fill(action["selector"], action["value"])
                        history.append(f"Filled {action['selector']} with '{action['value']}'")
                    except Exception as e:
                        history.append(f"Fill failed: {e}")

                elif action["action"] == "done":
                    result_summary = action.get("result", "Task completed.")
                    print(f"\n  ✓ Done: {result_summary}")
                    break

                elif action["action"] == "failed":
                    result_summary = action.get("result", "Task failed.")
                    print(f"\n  ✗ Failed: {result_summary}")
                    break

                await asyncio.sleep(1)  # be kind to rate limits

        except Exception as e:
            result_summary = f"Error: {e}"
            print(f"\n  Exception: {e}")
        finally:
            await asyncio.sleep(1)
            await browser.close()

        print(f"\n{'='*60}")
        print("AGENT RESULT")
        print(f"{'='*60}")
        print(result_summary)
        print(f"{'='*60}\n")
        return result_summary


def main():
    if len(sys.argv) < 2:
        print(f"\nUsage: python agent.py \"reset password for john@company.com\"")
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    asyncio.run(run_it_task(task))


if __name__ == "__main__":
    main()