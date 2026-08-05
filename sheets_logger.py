from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any, Mapping

from ledger.telemetry import ALLOWED_TELEMETRY_FIELDS, validate_telemetry_payload


SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")


def save_telemetry_event(payload: Mapping[str, Any]) -> bool:
    """Append only allowlisted, privacy-safe decision metadata to Sheets."""
    safe_payload = validate_telemetry_payload(payload)
    if not SPREADSHEET_ID or not CREDENTIALS_JSON:
        return False

    import gspread
    from google.oauth2.service_account import Credentials

    credentials = Credentials.from_service_account_info(
        json.loads(CREDENTIALS_JSON),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    sheet = gspread.authorize(credentials).open_by_key(SPREADSHEET_ID).sheet1
    ordered_fields = sorted(ALLOWED_TELEMETRY_FIELDS)
    sheet.append_row(
        [datetime.now(UTC).isoformat()]
        + [safe_payload.get(field) for field in ordered_fields]
    )
    return True
