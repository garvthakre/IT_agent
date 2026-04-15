"""
agent.py — IT Support AI Agent
================================
Uses direct Playwright to control the IT Admin Panel.
"""

import asyncio
import sys
import os
import re
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER       = os.getenv("AI_PROVIDER", "groq").lower()
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL        = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-5")
ADMIN_PANEL_URL   = os.getenv("ADMIN_PANEL_URL", "http://localhost:5000")


def validate_env():
    required = {
        "groq":      ("GROQ_API_KEY",     GROQ_API_KEY),
        "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
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
            max_tokens=2048,
        )
    if AI_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=ANTHROPIC_MODEL,
            anthropic_api_key=ANTHROPIC_API_KEY,
            temperature=0.0,
            max_tokens=512,
        )


def sanitize_selector(selector: str) -> str:
    """
    Translate invalid jQuery-style :contains() selectors into
    Playwright-compatible text= locators so clicks don't crash.
    """
    if not selector:
        return selector
    match = re.search(r":contains\(['\"](.+?)['\"]\)", selector)
    if match:
        return f"text={match.group(1)}"
    return selector


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

        async def navigate(url: str):
            await page.goto(url)
            await page.wait_for_load_state("networkidle")

        async def ask_llm(page_html: str, history: list) -> dict:
            history_text = "\n".join(history[-6:]) if history else "None yet"

            prompt = f"""You are controlling an IT ADMIN PANEL at {ADMIN_PANEL_URL}.

THIS IS AN ADMIN PANEL — NOT A USER-FACING WEBSITE.
- There is NO login page. NEVER navigate to /login, /forgot-password, or any URL outside this panel.
- Valid URLs:
    {ADMIN_PANEL_URL}/              (dashboard)
    {ADMIN_PANEL_URL}/users         (user list + search)
    {ADMIN_PANEL_URL}/create-user   (create user form)
    {ADMIN_PANEL_URL}/reset-password/<id>   (reached via link, not typed directly)

════════════════════════════════════════
HOW TO USE EXACT SELECTORS (IMPORTANT)
════════════════════════════════════════
NEVER use :contains() — it is not valid CSS and will always fail.

Search box:         input[name="search"]
Search submit:      button[type="submit"]

After searching, each user row has id="user-<id>" (e.g. id="user-3").
To act on a specific user row, use:
  Reset Password link:   #user-<id> a[href^="/reset-password/"]
  Disable/Enable button: #user-<id> form[action^="/toggle-status/"] button
  Delete button:         #user-<id> form[action^="/delete-user/"] button

If you don't know the user's id yet, use partial attribute selectors:
  First Reset Password link on page:  a[href^="/reset-password/"]
  First Disable button on page:       form[action^="/toggle-status/"] button
  First Enable button on page:        form[action^="/toggle-status/"] button

Create user form fields:
  Name:   input[name="name"]        — action=fill
  Email:  input[name="email"]       — action=fill
  Role:   select[name="role"]       — action=fill, value must be exactly one of: employee | admin | viewer
                                      (this is a <select> dropdown — use action=fill, the system handles it)
  Submit: button[type="submit"]     — action=click, ONLY after filling name, email, and role

Reset password confirmation page:
  Confirm button: button[type="submit"]

════════════════════════════════════════
STEP-BY-STEP PLAYBOOK
════════════════════════════════════════
Reset a password:
  1. navigate → {ADMIN_PANEL_URL}/users
  2. fill input[name="search"] with the user's email
  (search auto-submits — do NOT add an extra click for search button)
  3. click a[href^="/reset-password/"]
  4. click button[type="submit"]   ← confirms reset
  5. done

Disable/Enable an account:
  1. navigate → {ADMIN_PANEL_URL}/users
  2. fill input[name="search"] with the user's email
  (search auto-submits — do NOT add an extra click for search button)
  3. click form[action^="/toggle-status/"] button
  4. done

Create a user:
  1. navigate → {ADMIN_PANEL_URL}/create-user
  2. fill input[name="name"] with full name
  3. fill input[name="email"] with email
  4. fill select[name="role"] with role (employee / admin / viewer)
  5. click button[type="submit"]
  6. done

Check if user exists then act:
  1. navigate → {ADMIN_PANEL_URL}/users
  2. fill input[name="search"] with the user's email
  3. Read the HTML — if "No users found" appears, user does not exist → go to create-user
  4. If user exists → perform the required action directly

════════════════════════════════════════
CURRENT PAGE HTML (first 3000 chars):
{page_html[:3000]}

RECENT ACTIONS:
{history_text}

TASK: {task}

════════════════════════════════════════
RULES
════════════════════════════════════════
- If you see a 404 page or wrong page, navigate to {ADMIN_PANEL_URL}/users.
- If task is complete (confirmation page with checkmark visible in HTML), respond action=done.
- NEVER repeat the same failed action twice — try a different selector or approach.
- NEVER use :contains() in any selector.
- For the create-user form: fill name → fill email → fill role → click submit. Do NOT skip or repeat steps.
- The search input auto-submits on Enter — after filling search, go straight to clicking the action button.

Respond with ONLY valid JSON, no markdown, no explanation:
{{
  "action": "navigate" | "click" | "fill" | "done" | "failed",
  "url": "<full url — only if action=navigate>",
  "selector": "<css selector — only if action=click or fill>",
  "value": "<text — only if action=fill>",
  "result": "<summary — only if action=done or failed>"
}}"""

            response = llm.invoke(prompt)
            text = response.content.strip()

            # Strip markdown code fences if present
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

        history        = []
        result_summary = "No result"
        last_actions   = []

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

                act      = action.get("action", "")
                selector = sanitize_selector(action.get("selector") or "")
                url      = action.get("url", "")
                value    = action.get("value", "")
                result   = action.get("result", "")

                action_str = f"{act}:{url or selector}"
                print(f"{act} — {url or selector or result}")

                # ── Loop detection ─────────────────────────────────────────
                last_actions.append(action_str)
                if len(last_actions) > 3 and len(set(last_actions[-3:])) == 1:
                    print(f"\n  ⚠ Loop detected on: {action_str} — forcing recovery")
                    current_url = page.url

                    if "create-user" in current_url:
                        # Stuck on create-user form — try force-submitting whatever is filled
                        print("  ↳ On create-user page — attempting force submit")
                        try:
                            await page.click("button[type='submit']", timeout=3000)
                            await page.wait_for_load_state("networkidle")
                            history.append("Loop on create-user — force-submitted form")
                        except Exception:
                            await navigate(ADMIN_PANEL_URL + "/users")
                            history.append("Loop — force submit failed, reset to /users")
                    else:
                        await navigate(ADMIN_PANEL_URL + "/users")
                        history.append("Loop detected — reset to /users")

                    last_actions = []
                    await asyncio.sleep(1)
                    continue

                # ── Block bad / external URLs ──────────────────────────────
                if act == "navigate" and url:
                    bad = (
                        "/login" in url
                        or "/forgot" in url
                        or "/password-reset" in url
                        or not url.startswith(ADMIN_PANEL_URL)
                    )
                    if bad:
                        print(f"  ⛔ Blocked bad URL: {url} — redirecting to /users")
                        await navigate(ADMIN_PANEL_URL + "/users")
                        history.append(f"Blocked bad URL {url} — went to /users")
                        await asyncio.sleep(1)
                        continue

                # ── Execute action ─────────────────────────────────────────
                if act == "navigate":
                    await navigate(url)
                    history.append(f"Navigated to {url}")

                elif act == "click":
                    try:
                        await page.click(selector, timeout=5000)
                        await page.wait_for_load_state("networkidle")
                        history.append(f"Clicked {selector}")
                    except Exception as e:
                        print(f"\n    Click failed ({e}) — trying locator.first")
                        try:
                            await page.locator(selector).first.click(timeout=5000)
                            await page.wait_for_load_state("networkidle")
                            history.append(f"Clicked (locator.first) {selector}")
                        except Exception as e2:
                            print(f"\n    locator.first also failed: {e2}")
                            history.append(f"Click failed entirely for {selector}: {e2}")

                elif act == "fill":
                    try:
                        # Detect <select> elements and use select_option instead of fill
                        tag = await page.locator(selector).first.evaluate(
                            "el => el.tagName.toLowerCase()"
                        )
                        if tag == "select":
                            await page.select_option(selector, value)
                            history.append(f"Selected '{value}' in {selector}")
                        else:
                            await page.fill(selector, value)
                            history.append(f"Filled {selector} with '{value}'")
                            # Auto-submit search form by pressing Enter
                            if "search" in selector.lower():
                                await page.press(selector, "Enter")
                                await page.wait_for_load_state("networkidle")
                                history.append("Pressed Enter to submit search")
                    except Exception as e:
                        history.append(f"Fill/select failed: {e}")

                elif act == "done":
                    result_summary = result or "Task completed."
                    print(f"\n  ✓ Done: {result_summary}")
                    break

                elif act == "failed":
                    result_summary = result or "Task failed."
                    print(f"\n  ✗ Failed: {result_summary}")
                    break

                await asyncio.sleep(1)

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
        print(f'\nUsage: python agent.py "reset password for john@company.com"')
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    asyncio.run(run_it_task(task))


if __name__ == "__main__":
    main()