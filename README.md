# IT Support AI Agent

An AI agent that accepts natural-language IT support requests and autonomously carries them out on a web-based admin panel — navigating, clicking, and filling forms just like a human operator would.

---

## Demo

> Agent completing 4 IT tasks end-to-end, including a multi-step conditional task.

*(https://www.loom.com/share/7f4dfdad1c564551baee99233a2d7758)*

---

## What It Does

| Request | What the agent does |
|---|---|
| `"Reset password for john@company.com"` | Searches for user → navigates to reset page → confirms reset → returns new temp password |
| `"Create employee alex@company.com"` | Opens create-user form → fills name, email, role → submits |
| `"Disable emily@company.com"` | Finds user → clicks Disable Account |
| `"Check if charlie@company.com exists, create if not, then disable"` | Searches → creates if missing → disables account (multi-step conditional) |

---

## Architecture

```
User prompt (CLI)
      │
      ▼
  agent.py  ──────────────────────────────────────────────┐
      │                                                    │
      │  1. Navigate to admin panel                        │
      │  2. Extract page HTML                              │
      │  3. Send HTML + task + history to LLM              │
      │  4. LLM returns next action as JSON                │
      │  5. Playwright executes action                     │
      │  6. Repeat until done / max steps reached          │
      │                                                    │
      ▼                                                    │
  Playwright (browser automation)                         │
      │                                                    │
      ▼                                                    │
  Flask Admin Panel (localhost:5000)  ◄────────────────────┘
      │
      ▼
  SQLite database
```

**Key design decisions:**

- **Custom agent loop over browser-use library** — gives full control over prompt engineering, action parsing, loop detection, and error recovery. More reliable against a known panel UI.
- **LLM reads raw HTML, not screenshots** — works with any text-capable LLM (Groq's free Llama models included), no vision API required.
- **Provider-agnostic** — swap between Groq (free, fast) and Anthropic via a single `.env` variable.
- **Loop detection** — agent detects if it's repeating the same action 3 times and forces a recovery step.
- **Selector sanitization** — invalid jQuery-style `:contains()` selectors are automatically translated to Playwright-compatible locators.

---

## Project Structure

```
IT_agent/
├── admin-panel/
│   ├── app.py              # Flask admin panel (routes + logic)
│   ├── init_db.py          # Seeds SQLite database with sample users
│   ├── requirements.txt
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── users.html
│       ├── user_detail.html
│       ├── create_user.html
│       ├── reset_confirm.html
│       └── confirm.html
│
└── agent/
    ├── agent.py            # AI agent — LLM loop + Playwright execution
    ├── demo.py             # Runs 4 preset demo tasks sequentially
    ├── requirements.txt
    └── .env.example        # Environment variable template
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/IT_agent.git
cd IT_agent
```

### 2. Start the admin panel

```bash
cd admin-panel
pip install -r requirements.txt
python init_db.py        # creates and seeds database.db
python app.py            # starts Flask at http://localhost:5000
```

### 3. Configure the agent

```bash
cd ../agent
cp .env.example .env
```

Edit `.env`:

```env
# Choose provider: groq (free) or anthropic (paid)
AI_PROVIDER=groq

GROQ_API_KEY=your_key_here          # https://console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile

# Or for Anthropic:
# ANTHROPIC_API_KEY=your_key_here
# ANTHROPIC_MODEL=claude-opus-4-5

ADMIN_PANEL_URL=http://localhost:5000
```

### 4. Install agent dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 5. Run a task

```bash
python agent.py "reset password for john@company.com"
python agent.py "disable the account for emily@company.com"
python agent.py "create a new employee: name Alex Turner, email alex@company.com"
```

Or run the full demo sequence:

```bash
python demo.py
```

---

## Admin Panel

A minimal Flask + SQLite admin panel with 4 core IT operations:

| Action | Route |
|---|---|
| View all users | `GET /users` |
| Create user | `GET/POST /create-user` |
| Reset password | `GET/POST /reset-password/<id>` |
| Enable / Disable account | `POST /toggle-status/<id>` |
| Delete user | `POST /delete-user/<id>` |

Seeded with 8 sample users across admin, employee, and viewer roles.

---

## LLM Providers

| Provider | Cost | Recommended model | Notes |
|---|---|---|---|
| **Groq** | Free tier | `llama-3.3-70b-versatile` | Fast, recommended for dev |
| **Anthropic** | Paid | `claude-opus-4-5` | More capable for complex tasks |

Set `AI_PROVIDER=groq` or `AI_PROVIDER=anthropic` in `.env`.

---

## Requirements

- Python 3.10+
- Node.js not required
- Chromium (installed via `playwright install chromium`)
- Groq API key (free at [console.groq.com](https://console.groq.com)) or Anthropic API key