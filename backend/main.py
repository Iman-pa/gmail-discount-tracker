from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Gmail Discount Tracker API")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8000/auth/google/callback"

# Temporarily holds the PKCE code_verifier for each in-flight OAuth attempt,
# keyed by the state parameter Google echoes back in the callback.
_pending_verifiers: dict[str, str] = {}


def _build_flow():
    return Flow.from_client_config(
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


@app.get("/")
def root():
    return {"message": "Gmail Discount Tracker API is running"}


@app.get("/auth/google")
def auth_google():
    flow = _build_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )
    _pending_verifiers[state] = flow.code_verifier
    return RedirectResponse(authorization_url)


@app.get("/auth/google/callback")
def auth_google_callback(request: Request):
    state = request.query_params.get("state")
    code_verifier = _pending_verifiers.pop(state, None)

    flow = _build_flow()
    flow.fetch_token(
        code=request.query_params.get("code"),
        code_verifier=code_verifier,
    )

    credentials = flow.credentials
    service = build("gmail", "v1", credentials=credentials)
    profile = service.users().getProfile(userId="me").execute()

    return {
        "message": "Gmail OAuth successful",
        "email": profile.get("emailAddress"),
        "messages_total": profile.get("messagesTotal"),
    }
