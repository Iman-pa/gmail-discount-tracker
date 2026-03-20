from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Gmail Discount Tracker API")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8000/auth/google/callback"

DISCOUNT_QUERY = (
    "category:promotions "
    "(off OR discount OR promo OR coupon OR free OR save OR deal OR \"%off\" OR deal)"
)

# Temporarily holds the PKCE code_verifier for each in-flight OAuth attempt,
# keyed by the state parameter Google echoes back in the callback.
_pending_verifiers: dict[str, str] = {}

# Stores OAuth credentials after a successful login, keyed by email address.
_credentials_store: dict[str, object] = {}


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


def _get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


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

    email = profile.get("emailAddress")
    _credentials_store[email] = credentials

    return {
        "message": "Gmail OAuth successful",
        "email": email,
        "messages_total": profile.get("messagesTotal"),
    }


@app.get("/discounts")
def get_discounts(
    email: str = Query(..., description="Email address used during OAuth login"),
    max_results: int = Query(default=50, ge=1, le=200),
):
    credentials = _credentials_store.get(email)
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="No credentials found for this email. Please authenticate first via /auth/google.",
        )

    service = build("gmail", "v1", credentials=credentials)

    results = service.users().messages().list(
        userId="me",
        q=DISCOUNT_QUERY,
        maxResults=max_results,
    ).execute()

    message_refs = results.get("messages", [])
    if not message_refs:
        return {"email": email, "count": 0, "emails": []}

    emails = []
    for ref in message_refs:
        msg = service.users().messages().get(
            userId="me",
            id=ref["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()

        headers = msg.get("payload", {}).get("headers", [])
        emails.append({
            "id": ref["id"],
            "sender": _get_header(headers, "From"),
            "subject": _get_header(headers, "Subject"),
            "date": _get_header(headers, "Date"),
        })

    return {"email": email, "count": len(emails), "emails": emails}