"""
Generates a Google Ads OAuth2 refresh token.
Run this once, copy the printed refresh token into your .env file.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=["https://www.googleapis.com/auth/adwords"],
)

credentials = flow.run_local_server(port=8080, open_browser=True)

print("\n" + "="*60)
print("SUCCESS — Add this to your .env file:")
print("="*60)
print(f"GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}")
print("="*60 + "\n")
