from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Gmail Discount Tracker API")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8000/auth/google/callback"


@app.get("/")
def root():
    return {"message": "Gmail Discount Tracker API is running"}


@app.get("/auth/google")
def auth_google():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )
    return RedirectResponse(authorization_url)
