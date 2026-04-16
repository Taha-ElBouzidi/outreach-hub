# CLAUDE.md — AI Agent Onboarding Document
# Evernex Outreach Hub V9.0

This file is the **single source of truth** for any AI agent (Claude, Gemini, etc.) picking up development on this project. Read this entire file before writing a single line of code.

---

## 1. What This Project Is

**Evernex Outreach Hub V9.0** is a premium, SaaS-grade desktop automation platform built with Python + CustomTkinter. It allows Evernex sales reps to run multi-channel outreach campaigns (LinkedIn, Outlook, Gmail) at scale, with account-based quotas, Supabase telemetry, and a Boutique UI aesthetic.

---

## 2. How to Set Up on a New Machine

```bash
# 1. Clone
git clone https://github.com/Taha-ElBouzidi/outreach-hub.git
cd outreach-hub

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python 02_Apps/outreach_hub_v9.py
```

> **Requires:** Python 3.10+, Google Chrome installed.

---

## 3. Project Structure

```
outreach-hub/
├── 01_Engines/
│   ├── account_manager.py    # Auth + Supabase REST API (DO NOT use supabase-py)
│   ├── csv_parser.py         # CSV/JSON/XLSX ingestion + template variable mapping
│   ├── outlook_engine.py     # OWA Selenium automation
│   ├── gmail_engine.py       # Gmail Selenium automation
│   └── link.py               # LinkedIn Selenium automation
├── 02_Apps/
│   └── outreach_hub_v9.py    # Main UI — ALL CustomTkinter code lives here
├── 04_Assets/                # Icons, branding (empty for now)
├── 05_Docs/
│   └── UI_Research_2026.md   # Design guidelines & research
├── requirements.txt
├── README.md
└── CLAUDE.md                 # ← You are here
```

---

## 4. Architecture & Critical Rules

### Backend (01_Engines/)
- **account_manager.py** uses pure `urllib` for all Supabase REST calls. **NEVER** use the `supabase-py` library — it has C++ dependency issues on Windows.
- Supabase project URL: `https://aqmfotkcmjukenuflvhv.supabase.co`
- Supabase publishable key: `sb_publishable_bsw1uD3Kx05YkT0BifnUxA_Y9ewa7Ae`
- Auth: Username + Activation Key. Session persisted to `.evernex_outreach_session_v9` (gitignored).

### Frontend (02_Apps/outreach_hub_v9.py)
- Built with `customtkinter`. **No web frameworks.**
- UI is strictly separate from backend — all business logic is in `01_Engines/`.
- **Port Registry (hardcoded, do not change):**
  - LinkedIn → `9222`
  - Outlook → `9223`
  - Gmail → `9224`

### Email Branding Rule (MANDATORY)
All outreach email bodies MUST use HTML: Font `Calibri`, size `10pt`. Key terms (`Evernex`, `Global TPM Provider`, etc.) must be bolded. See `outlook_engine.apply_evernex_styling()`.

---

## 5. UI Design System

### Color Palette — "Boutique / Coffee"
| Token | Hex | Usage |
|---|---|---|
| `bg_dark` | `#ffe6a7` | App cream background |
| `bg_sidebar` | `#6f1d1b` | Heavy Burgundy sidebar |
| `bg_card` | `#bb9457` | Soft Gold cards |
| `bg_input` | `#f0d89c` | Muted cream inputs |
| `accent` | `#432818` | Dark Cocoa — primary action buttons |
| `red` | `#6f1d1b` | Burgundy — destructive / stop |
| `text_sidebar` | `#ffe6a7` | Cream text on dark sidebar |

### Animation Conventions
- **Loading Curtain:** `_slide_curtain_down()` — Burgundy overlay slides down at 60FPS (16ms `after()` loop) to reveal the app on login.
- **CTkSwitch toggle:** Native iOS-style day/night switch for "Custom JSON ↔ Sequence" mode. Styled Burgundy/Gold.
- **DO NOT** use `.place()` for layout — only for the curtain animation overlay.
- **DO NOT** use staggered `.grid()` loading — it breaks the scrollbar.

### Layout
- Sidebar: fixed 240px wide, `pack(side="left", fill="y")`
- Main content: `CTkScrollableFrame` packed to the right — **always use this for scrolling, not a plain CTkFrame**
- Cards use `.pack(fill="x", padx=30, pady=15)` inside the scroll frame

---

## 6. Subscription Tiers (Supabase `accounts` table)

| Tier | Daily Limit | Monthly Limit | Channels |
|---|---|---|---|
| `free` | 10 | 100 | LinkedIn only |
| `starter` | 350 | 10,500 | LinkedIn + Outlook |
| `pro` | 1,000 | 30,000 | All channels |
| `admin` | ∞ | ∞ | All channels |

Quota is enforced in `account_manager.Account.can_send()` — check this before any campaign.

---

## 7. Known Issues & Fixes Applied

| Issue | Fix |
|---|---|
| `CTkSwitch` crash on Python 3.14 | Wrap in a transparent `CTkFrame` and `.pack()` the switch inside it; `.grid()` the wrapper |
| `link.py` has no `start_browser()` | Browser launch is handled directly in the UI via `subprocess.Popen` with Chrome debug port args |
| Gradient Canvas toggle was too large | Replaced with native `CTkSwitch` (day/night style) |
| `.place()` animation broke scrollbar | Replaced with Curtain overlay that is destroyed after animation completes |

---

## 8. What Was Done Last Session (April 16 2026)

- ✅ Full UI rewrite with Boutique color palette
- ✅ Replaced `CTkSegmentedButton` with `CTkSwitch` day/night toggle
- ✅ Built 60FPS `_slide_curtain_down()` entrance animation
- ✅ Restored scrolling via `CTkScrollableFrame`
- ✅ Fixed `link.py` missing `start_browser` — moved browser launch to UI layer
- ✅ Fixed `CTkSwitch` pack/grid crash on Python 3.14
- ✅ Initialized Git repo and pushed to GitHub
- ✅ Added `requirements.txt`, `README.md`, `.gitignore`, `CLAUDE.md`

---

## 9. Next Steps (Prioritized)

1. **AI Auto-Mode (Gemini Integration)** — Build a Gemini-powered email/LinkedIn message generator. User picks tone (Professional / Direct / Friendly), inputs prospect data, and Gemini drafts personalized outreach. Add a new sidebar section "🤖 AI Mode".
2. **PyInstaller Encrypted Build** — See Section 11 below for the full anti-cracking strategy. **Do NOT build a plain unprotected exe.**
3. **UI Layout Rework** — The user wants to further optimize the layout. Cards could be made more compact and the log feed could show richer metadata (timestamp per entry, color-coded status).
4. **Git PATH fix on Windows** — Add `C:\Users\telbouzidi\AppData\Local\Programs\Git\cmd` to system PATH permanently so `git` works in any terminal without full path.

---

## 10. Developer Notes

- Always test with `python 02_Apps/outreach_hub_v9.py` from the repo root or the `02_Apps/` folder.
- The app runs fine without the Selenium engines loaded — it gracefully degrades if `link.py`, `outlook_engine.py`, or `gmail_engine.py` fail to import.
- Session file (`.evernex_outreach_session_v9`) is gitignored — each machine needs to log in once to create a fresh session.

---

## 11. Anti-Cracking & Encrypted Build Strategy

> ⚠️ **MANDATORY** — Never distribute a raw PyInstaller `.exe`. The bytecode can be trivially extracted and decompiled. Use the 3-layer approach below.

### Layer 1: Pyarmor Bytecode Obfuscation
**Pyarmor** wraps every `.py` file so that the bytecode is encrypted and cannot be decompiled back to Python source, even after extraction from the `.exe`.

```bash
pip install pyarmor

# Obfuscate the entire source tree into a dist/ folder
pyarmor gen --output dist_obfuscated 02_Apps/outreach_hub_v9.py 01_Engines/
```

The output in `dist_obfuscated/` contains runtime-encrypted `.pyc` files that require the Pyarmor runtime library to execute. Without it, the code is unreadable.

### Layer 2: PyInstaller with AES-256 Bytecode Encryption
Build the `.exe` FROM the obfuscated output, not the raw source. Add the `--key` flag to apply an additional AES-256 encryption layer on top of Pyarmor:

```bash
pip install pyinstaller

pyinstaller \
  --onefile \
  --noconsole \
  --name "EvernexOutreachHub" \
  --icon "04_Assets/icon.ico" \
  dist_obfuscated/outreach_hub_v9.py
```

> **Note:** `--key` for PyInstaller AES encryption requires `pycryptodome`: `pip install pycryptodome`

### Layer 3: Server-Side License Validation (Most Critical)
This is the **strongest protection** — even if someone cracks layers 1 and 2, the app is useless without a valid live server response from Supabase.

The current `account_manager.authenticate()` already does this correctly:
- Every app launch calls Supabase to verify the username + activation key.
- If Supabase is unreachable OR the key is revoked, the app refuses to open.
- **Never store the activation key in a local file in plaintext** — the session file only stores an encrypted token reference (already implemented).

### Build Checklist (When Ready)
- [ ] `pip install pyarmor pyinstaller pycryptodome`
- [ ] Run Pyarmor obfuscation on source
- [ ] Run PyInstaller on obfuscated output with `--onefile --noconsole`
- [ ] Test the `.exe` on a machine without Python installed
- [ ] Verify that the app refuses to launch if the Supabase key is wrong or revoked
- [ ] Place final `.exe` in `04_Assets/builds/` (gitignored via `*.exe` rule)

### Add to .gitignore
```
# Build outputs
dist/
dist_obfuscated/
build/
*.exe
*.spec
04_Assets/builds/
```

