"""
csv_parser.py
-------------
Evernex Outreach Hub - V9.0 CSV/Excel Parser Engine.
Converts raw CSV/XLSX files into the JSON format required by the engines.
Supports auto-detection of column names and graceful fallback.
"""

import os
import json
import csv


# ---------------------------------------------------------------------------
# COLUMN MAPPING — Flexible detection of common CSV headers
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    "first_name": ["first name", "firstname", "first", "prénom", "prenom"],
    "last_name": ["last name", "lastname", "last", "surname", "nom", "family name"],
    "email": ["email", "e-mail", "email address", "work email", "mail"],
    "company": ["company", "company name", "organization", "société", "societe", "employer"],
    "job_title": ["job title", "title", "position", "job position", "role", "job"],
    "city": ["city", "location", "ville", "metro", "region"],
    "linkedin_url": ["linkedin url", "linkedin", "linkedin profile", "profile url", "url"],
    "phone": ["phone", "phone number", "mobile", "telephone", "tel"],
}


def _normalize(header):
    """Normalize a header string for matching."""
    return str(header).strip().lower().replace("_", " ")


def _detect_columns(headers):
    """Auto-detect which CSV columns map to our internal fields."""
    mapping = {}
    normalized_headers = [_normalize(h) for h in headers]

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized_headers:
                idx = normalized_headers.index(alias)
                mapping[field] = headers[idx]  # Use original header name
                break

    return mapping


def parse_csv(file_path):
    """
    Parse a CSV file and return a list of prospect dicts.
    Auto-detects columns. Returns (data_list, detected_columns, error_msg).
    """
    try:
        rows = []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            if not headers:
                return [], {}, "CSV file has no headers."

            col_map = _detect_columns(headers)

            for row in reader:
                prospect = {}
                for field, csv_col in col_map.items():
                    prospect[field] = str(row.get(csv_col, "")).strip()

                # Skip completely empty rows
                if not any(prospect.values()):
                    continue

                rows.append(prospect)

        return rows, col_map, None

    except Exception as e:
        return [], {}, f"CSV Parse Error: {str(e)}"


def parse_excel(file_path):
    """
    Parse an Excel (.xlsx) file and return a list of prospect dicts.
    Auto-detects columns. Returns (data_list, detected_columns, error_msg).
    """
    try:
        import openpyxl
    except ImportError:
        return [], {}, "openpyxl not installed. Cannot read Excel files."

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)

        # First row = headers
        headers = [str(h) if h else "" for h in next(rows_iter)]
        col_map = _detect_columns(headers)

        rows = []
        for row in rows_iter:
            prospect = {}
            for field, csv_col in col_map.items():
                col_idx = headers.index(csv_col)
                val = row[col_idx] if col_idx < len(row) else ""
                prospect[field] = str(val).strip() if val else ""

            if not any(prospect.values()):
                continue

            rows.append(prospect)

        wb.close()
        return rows, col_map, None

    except Exception as e:
        return [], {}, f"Excel Parse Error: {str(e)}"


def parse_file(file_path):
    """
    Universal parser — detects file type and delegates.
    Returns (data_list, detected_columns, error_msg).
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        return parse_csv(file_path)
    elif ext in [".xlsx", ".xls"]:
        return parse_excel(file_path)
    elif ext == ".json":
        # Pass-through for JSON files (backward compatibility with V8.8)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data, {"json": "direct"}, None
        except Exception as e:
            return [], {}, f"JSON Parse Error: {str(e)}"
    else:
        return [], {}, f"Unsupported file type: {ext}"


def convert_to_linkedin_json(prospects):
    """Convert parsed prospects to LinkedIn engine format."""
    result = []
    for p in prospects:
        url = p.get("linkedin_url", "")
        if not url:
            continue
        result.append({
            "name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "linkedin_url": url,
            "final_outreach": "",
            "connection_status": ""
        })
    return result


def convert_to_email_json(prospects):
    """Convert parsed prospects to Email engine format (Outlook/Gmail)."""
    result = []
    for p in prospects:
        email = p.get("email", "")
        if not email:
            continue
        name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        result.append({
            "prospect_name": name,
            "first_name": p.get("first_name", ""),
            "last_name": p.get("last_name", ""),
            "email": email,
            "company": p.get("company", ""),
            "job_title": p.get("job_title", ""),
            "city": p.get("city", ""),
            "status": "pending"
        })
    return result


def apply_template_variables(template, prospect):
    """
    Replace dynamic variables in a template string with prospect data.
    Supports: [first_name], [last_name], [company], [job_title], [email], [city]
    Also supports legacy: [prospect name]
    """
    replacements = {
        "[first_name]": prospect.get("first_name", ""),
        "[last_name]": prospect.get("last_name", ""),
        "[company]": prospect.get("company", ""),
        "[job_title]": prospect.get("job_title", ""),
        "[email]": prospect.get("email", ""),
        "[city]": prospect.get("city", ""),
        # Legacy V8 compatibility
        "[prospect name]": prospect.get("first_name", prospect.get("prospect_name", "there")),
    }

    result = template
    for var, val in replacements.items():
        result = result.replace(var, val if val else "")

    return result
