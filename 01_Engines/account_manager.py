"""
account_manager.py
-------------------
Evernex Outreach Hub - V9.0 Account & Access Control Engine.
Handles remote account verification via Supabase REST API, per-user permissions, 
dual-quota limits (Monthly & Daily), and session caching.
No external dependencies required (uses urllib).
"""

import os
import json
import calendar
import urllib.request
import urllib.error
from datetime import datetime, date

# ==========================================================================
# CONFIG & SUPABASE SETUP
# ==========================================================================
SUPABASE_URL = "https://aqmfotkcmjukenuflvhv.supabase.co"
SUPABASE_KEY = "sb_publishable_bsw1uD3Kx05YkT0BifnUxA_Y9ewa7Ae"
LOCAL_SESSION_FILE = os.path.join(os.path.expanduser("~"), ".evernex_outreach_session_v9")

# ==========================================================================
# TIER DEFINITIONS (Dual-Quota System)
# ==========================================================================
TIERS = {
    "admin": {
        "label": "Admin",
        "color": "#a29bfe",
        "monthly_limit": -1,  # Unlimited
        "daily_limit": -1,    # Unlimited
        "features": ["csv_import", "sequence", "custom_json", "ai_auto"],
    },
    "enterprise": {
        "label": "Enterprise",
        "color": "#00b894",
        "monthly_limit": -1,
        "daily_limit": -1,
        "features": ["csv_import", "sequence", "custom_json", "ai_auto"],
    },
    "scale_40": {
        "label": "Scale ($40)",
        "color": "#6c5ce7",
        "monthly_limit": 100000,
        "daily_limit": 3350,
        "features": ["csv_import", "sequence", "custom_json", "ai_auto"],
    },
    "pro_20": {
        "label": "Pro ($20)",
        "color": "#0984e3",
        "monthly_limit": 25000,
        "daily_limit": 850,
        "features": ["csv_import", "sequence", "custom_json", "ai_auto"],
    },
    "starter_10": {
        "label": "Starter ($10)",
        "color": "#00d6a4",
        "monthly_limit": 10000,
        "daily_limit": 350,
        "features": ["csv_import", "sequence", "custom_json"],
    },
    "free": {
        "label": "Free Trial",
        "color": "#fdcb6e",
        "monthly_limit": 150,  # Treated as "lifetime limit" for this tier
        "daily_limit": 10,
        "features": ["csv_import", "sequence", "custom_json"],
    },
    "banned": {
        "label": "Banned",
        "color": "#d63031",
        "monthly_limit": 0,
        "daily_limit": 0,
        "features": [],
    }
}

# ==========================================================================
# HELPER: SUPABASE REST REQUEST
# ==========================================================================
def sb_req(endpoint, method="GET", body=None):
    """Simple wrapper for Supabase REST API requests."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    # Replace spaces with %20 just in case
    url = url.replace(" ", "%20")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    data = json.dumps(body).encode('utf-8') if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            resp_body = res.read().decode('utf-8')
            return json.loads(resp_body) if resp_body else []
    except urllib.error.HTTPError as e:
        print(f"Supabase HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Supabase request failed: {e}")
        return None

# ==========================================================================
# ACCOUNT DATA CLASS
# ==========================================================================
class Account:
    """Represents an authenticated user account with current quota usage."""

    def __init__(self, db_data, usage_today=0, usage_month=0):
        self.id = db_data.get("id")
        self.username = db_data.get("username", "")
        self.display_name = db_data.get("display_name", self.username)
        self.key = db_data.get("license_key", "")
        self.tier = db_data.get("tier", "free")
        # Ensure channels is a parsed list, fallback to Outlook
        raw_channels = db_data.get("channels", ["Outlook"])
        self.channels = raw_channels if isinstance(raw_channels, list) else list(raw_channels)
        self.is_active = db_data.get("is_active", True)
        self.total_lifetime_emails = db_data.get("total_lifetime_emails", 0)
        
        self.usage_today = usage_today
        self.usage_month = usage_month

        tier_config = TIERS.get(self.tier, TIERS["free"])
        self.monthly_limit = tier_config["monthly_limit"]
        self.daily_limit = tier_config["daily_limit"]
        self.features = tier_config["features"]

    @property
    def tier_label(self):
        return TIERS.get(self.tier, TIERS["free"])["label"]

    @property
    def tier_color(self):
        return TIERS.get(self.tier, TIERS["free"])["color"]

    @property
    def is_banned(self):
        return self.tier == "banned" or not self.is_active

    def has_channel(self, channel):
        return channel in self.channels

    def has_feature(self, feature):
        return feature in self.features

    @property
    def quota_label(self):
        """Returns string displaying what's remaining to show in UI."""
        if self.daily_limit < 0:
            return "Unlimited"
            
        rem_daily = max(0, self.daily_limit - self.usage_today)
        
        if self.tier == "free":
            rem_life = max(0, self.monthly_limit - self.total_lifetime_emails)
            return f"{rem_daily}/day ({rem_life} total left)"
        else:
            rem_month = max(0, self.monthly_limit - self.usage_month)
            return f"{rem_daily}/day ({rem_month}/mo left)"

    def can_send(self, requested_amount=1):
        """Check if account has enough quota to send `requested_amount` of emails."""
        if self.is_banned:
            return False, "Your account is inactive or banned."

        if self.daily_limit >= 0:
            if (self.usage_today + requested_amount) > self.daily_limit:
                return False, f"Daily limit reached ({self.usage_today}/{self.daily_limit}). Please try again tomorrow."

        if self.monthly_limit >= 0:
            if self.tier == "free":
                if (self.total_lifetime_emails + requested_amount) > self.monthly_limit:
                    return False, f"Free trial limit reached ({self.total_lifetime_emails}/{self.monthly_limit}). Please upgrade."
            else:
                if (self.usage_month + requested_amount) > self.monthly_limit:
                    return False, f"Monthly limit reached ({self.usage_month}/{self.monthly_limit}). Please upgrade."

        return True, ""

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "license_key": self.key,
            "tier": self.tier,
            "channels": self.channels,
            "is_active": self.is_active,
            "total_lifetime_emails": self.total_lifetime_emails
        }

# ==========================================================================
# REMOTE AUTH & USAGE FETCHING
# ==========================================================================
def _get_usage_stats(account_id, tier):
    """Fetches daily and monthly usage for this account."""
    today = date.today().isoformat()
    _, last_day = calendar.monthrange(date.today().year, date.today().month)
    first_of_month = date.today().replace(day=1).isoformat()
    last_of_month = date.today().replace(day=last_day).isoformat()
    
    try:
        # Today's usage
        today_data = sb_req(f"usage_stats?select=emails_sent&account_id=eq.{account_id}&date=eq.{today}")
        usage_today = today_data[0]["emails_sent"] if today_data and isinstance(today_data, list) else 0

        if tier == "free":
            return usage_today, 0

        # Monthly usage
        month_data = sb_req(f"usage_stats?select=emails_sent&account_id=eq.{account_id}&date=gte.{first_of_month}&date=lte.{last_of_month}")
        usage_month = sum([row["emails_sent"] for row in month_data]) if month_data and isinstance(month_data, list) else 0
        
        return usage_today, usage_month
    except Exception as e:
        print(f"Error fetching usage stats: {e}")
        return 0, 0

def authenticate(username, key):
    """Authenticate username + key against Supabase."""
    try:
        data = sb_req(f"accounts?select=*&username=eq.{username.lower()}&license_key=eq.{key}")
        if data is None:
            return None, "System error connecting to Auth backend."
        if not data or not isinstance(data, list) or len(data) == 0:
            return None, "Invalid username or key."

        db_account = data[0]
        
        if not db_account.get("is_active"):
            return None, "Account is disabled or banned."

        tier = db_account.get("tier", "free")
        usage_today, usage_month = _get_usage_stats(db_account["id"], tier)

        account = Account(db_account, usage_today, usage_month)
        
        # Update last login
        sb_req(f"accounts?id=eq.{account.id}", method="PATCH", body={"last_login": datetime.now().isoformat()})
        
        return account, None
        
    except Exception as e:
        return None, f"Connection failed: {str(e)}"

# ==========================================================================
# TELEMETRY LOGGING
# ==========================================================================
def log_campaign_completion(account, channel, mode, total, sent, failed, start_time, duration_sec):
    """Log the campaign run and increment usage stats."""
    if not account or account.is_banned:
        return False

    today = date.today().isoformat()
    try:
        # 1. Add Campaign Log
        log_payload = {
            "account_id": account.id,
            "channel": channel,
            "campaign_mode": mode,
            "prospects_total": total,
            "prospects_sent": sent,
            "prospects_failed": failed,
            "started_at": start_time.isoformat() if hasattr(start_time, 'isoformat') else start_time,
            "finished_at": datetime.now().isoformat(),
            "duration_seconds": int(duration_sec)
        }
        sb_req("campaign_logs", method="POST", body=log_payload)

        # 2. Update Daily Usage Stat (Upsert-ish logic)
        resp = sb_req(f"usage_stats?select=id,emails_sent&account_id=eq.{account.id}&date=eq.{today}")
        if resp and len(resp) > 0:
            stat_id = resp[0]["id"]
            current_sent = resp[0]["emails_sent"]
            sb_req(f"usage_stats?id=eq.{stat_id}", method="PATCH", body={"emails_sent": current_sent + sent})
        else:
            sb_req("usage_stats", method="POST", body={"account_id": account.id, "date": today, "emails_sent": sent})

        # 3. If Free Tier, update total lifetime emails
        if account.tier == "free":
            sb_req(f"accounts?id=eq.{account.id}", method="PATCH", body={"total_lifetime_emails": account.total_lifetime_emails + sent})
            
        return True
    except Exception as e:
        print(f"Error logging telemetry: {e}")
        return False

# ==========================================================================
# LOCAL SESSION MANAGEMENT
# ==========================================================================
def save_session(account):
    try:
        with open(LOCAL_SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(account.to_dict(), f, indent=2)
        return True
    except:
        return False

def load_session():
    try:
        if not os.path.exists(LOCAL_SESSION_FILE):
            return None
        with open(LOCAL_SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Account(data, usage_today=0, usage_month=0)
    except:
        return None

def clear_session():
    try:
        if os.path.exists(LOCAL_SESSION_FILE):
            os.remove(LOCAL_SESSION_FILE)
        return True
    except:
        return False

def verify_session(account):
    if not account or not account.username or not account.key:
        return None, "No session."
    return authenticate(account.username, account.key)
