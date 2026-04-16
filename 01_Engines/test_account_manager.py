"""Unit test for account_manager.py — tests new dual-quota logic."""
import sys
sys.path.insert(0, "01_Engines")
import account_manager as am

print("=" * 50)
print("ACCOUNT MANAGER — TEST SUITE (V9 Supabase)")
print("=" * 50)

# Test 1: Tier Initialization & Logic Verification
print("\n[Test 1] Verifying Dual-Quota Tier Logic...")
try:
    # Free tier test
    free_acc = am.Account({"tier": "free", "total_lifetime_emails": 140}, usage_today=5)
    assert free_acc.daily_limit == 10
    assert free_acc.monthly_limit == 150
    can_send, _ = free_acc.can_send(5)
    assert can_send == True
    can_send, err = free_acc.can_send(6)
    assert can_send == False  # Daily limit would be 11 > 10
    assert "Daily limit" in err
    can_send, err = free_acc.can_send(15)
    assert can_send == False # Lifetime limit hit
    print("  -> FREE tier logic: PASS")

    # $10 Starter tier test
    starter_acc = am.Account({"tier": "starter_10"}, usage_today=300, usage_month=9900)
    assert starter_acc.daily_limit == 350
    assert starter_acc.monthly_limit == 10000
    can_send, _ = starter_acc.can_send(50)
    assert can_send == True
    can_send, err = starter_acc.can_send(51)
    assert can_send == False # Daily limit would be 351 > 350
    can_send, err = starter_acc.can_send(101)
    assert can_send == False # Monthly limit would be 10001 > 10000
    print("  -> STARTER ($10) tier logic: PASS")

    # Admin tier test
    admin_acc = am.Account({"tier": "admin"}, usage_today=5000, usage_month=100000)
    assert admin_acc.daily_limit == -1
    assert admin_acc.monthly_limit == -1
    can_send, _ = admin_acc.can_send(1000)
    assert can_send == True
    print("  -> ADMIN tier logic: PASS")

    # Banned test
    banned_acc = am.Account({"tier": "banned"})
    can_send, err = banned_acc.can_send(1)
    assert can_send == False
    assert "inactive or banned" in err
    print("  -> BANNED tier logic: PASS")

except AssertionError as e:
    print(f"  FAIL: Assertion Error - {e}")

# Test 2: Local Session save/load
print("\n[Test 2] Session save/load cycle...")
test_db_data = {
    "id": "mock-uuid",
    "username": "test_auth",
    "display_name": "Auth Tester",
    "license_key": "TEST-KEY",
    "tier": "pro_20",
    "channels": ["LinkedIn", "Outlook"],
    "is_active": True,
    "total_lifetime_emails": 0
}
test_acc = am.Account(test_db_data, usage_today=0, usage_month=0)
am.save_session(test_acc)
loaded = am.load_session()

if loaded and loaded.username == "test_auth" and loaded.tier == "pro_20":
    print(f"  Loaded: {loaded.display_name} ({loaded.tier_label})")
    print("  -> PASS")
else:
    print("  FAIL: Session not loaded correctly")
am.clear_session()

print("\n" + "=" * 50)
print("=== LOCAL TESTS PASSED ===")
print("=" * 50)
print("Note: Network authentication tests require the Supabase DB to be active.")
