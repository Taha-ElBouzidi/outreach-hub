"""Quick V9 unit test for csv_parser."""
import sys
sys.path.insert(0, "01_Engines")
import csv_parser

# Test 1: Variable replacement
p = {
    "first_name": "John",
    "last_name": "Doe",
    "company": "Meta",
    "job_title": "VP Infrastructure",
    "city": "New York"
}
template = "Hi [first_name], I see you work at [company] as [job_title] in [city]."
result = csv_parser.apply_template_variables(template, p)
print(f"Test 1 (Variables): {result}")
assert "John" in result and "Meta" in result, "FAIL"
print("  -> PASS\n")

# Test 2: Column detection
headers = ["First Name", "Last Name", "Work Email", "Company Name", "Title", "City"]
mapping = csv_parser._detect_columns(headers)
print(f"Test 2 (Columns): {mapping}")
assert "first_name" in mapping, "FAIL: first_name not detected"
assert "email" in mapping, "FAIL: email not detected"
assert "company" in mapping, "FAIL: company not detected"
print("  -> PASS\n")

# Test 3: Email JSON conversion
prospects = [p]
email_json = csv_parser.convert_to_email_json([{**p, "email": "john@meta.com"}])
print(f"Test 3 (Email JSON): {email_json}")
assert email_json[0]["prospect_name"] == "John Doe", "FAIL"
assert email_json[0]["email"] == "john@meta.com", "FAIL"
print("  -> PASS\n")

print("=== ALL TESTS PASSED ===")
