# Evernex Outreach Hub V9.0

A premium SaaS-grade outreach automation platform built with **CustomTkinter** and **Supabase**.

## Features

- **Multi-Channel Outreach** — LinkedIn, Outlook, and Gmail automation via Selenium
- **Account-Based Auth** — Username + Activation Key with Supabase backend
- **Quota Management** — Daily and monthly sending limits enforced per tier (Free / Starter / Pro / Admin)
- **Campaign Telemetry** — Real-time logging to Supabase `campaign_logs` and `usage_stats`
- **Boutique UI** — Deep Burgundy & Soft Gold aesthetic with 60FPS loading curtain animations
- **Template Engine** — Dynamic variable injection (`[first_name]`, `[company]`, etc.)

## Project Structure

```
Evernex_Outreach_Hub_V9/
├── 01_Engines/          # Core automation logic
│   ├── account_manager.py    # Supabase auth & quota enforcement
│   ├── csv_parser.py         # CSV/JSON/XLSX ingestion
│   ├── outlook_engine.py     # OWA automation
│   ├── gmail_engine.py       # Gmail automation
│   └── link.py               # LinkedIn automation
├── 02_Apps/             # GUI application
│   └── outreach_hub_v9.py    # Main UI (CustomTkinter)
├── 04_Assets/           # Branding & icons
└── 05_Docs/             # Documentation
```

## Quick Start

```bash
# Install dependencies
pip install customtkinter selenium webdriver-manager

# Run the app
python 02_Apps/outreach_hub_v9.py
```

## Subscription Tiers

| Tier | Daily Limit | Monthly Limit | Price |
|------|-------------|---------------|-------|
| Free | 10 | 100 | $0 |
| Starter | 350 | ~10,500 | $10 |
| Pro | 1,000 | 30,000 | $25 |
| Admin | ∞ | ∞ | Internal |

## Tech Stack

- **UI:** CustomTkinter (Python)
- **Backend:** Supabase (PostgreSQL REST API via urllib)
- **Automation:** Selenium + Chrome DevTools Protocol
- **Auth:** Username + Activation Key with session persistence
