# sheets_logger.py
import os
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")


def save_chat_log_to_sheet(user_id, user_message, assistant_reply):
    print("📄 [Sheets] 저장 시도 시작")

    if not SPREADSHEET_ID:
        print("❌ GOOGLE_SHEET_ID 누락")
        return

    if not CREDENTIALS_JSON:
        print("❌ GOOGLE_CREDENTIALS_JSON 누락")
        return

    try:
        creds_dict = json.loads(CREDENTIALS_JSON)

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )

        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sheet.append_row([
            now,
            str(user_id),
            user_message,
            assistant_reply
        ])

        print("✅ [Sheets] 저장 성공")

    except Exception as e:
        print("❌ [Sheets] 저장 실패:", e)
        import traceback
        traceback.print_exc()
