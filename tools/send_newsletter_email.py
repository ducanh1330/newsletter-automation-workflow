"""Create a Gmail draft, or (with --send) actually send, the newsletter HTML.

Usage:
    python tools/send_newsletter_email.py <path-to-html> --subject "..." [--recipients PATH] [--send]

Auth: uses credentials.json (OAuth client, downloaded from Google Cloud Console)
and caches a token in token.json after the first interactive consent.

Recipients are placed in Bcc so they don't see each other's addresses.
By default this creates a Gmail draft (review before sending yourself).
Pass --send to actually send the email immediately instead.

Images: build_newsletter_html.py embeds local images as base64 "data:" URIs,
which render fine in a browser but Gmail strips/ignores them in received
mail. So this script converts any data: URI <img> into a proper inline CID
attachment (multipart/related) before sending -- the format email clients
actually support for embedded images.
"""
import argparse
import base64
import json
import re
import sys
import uuid
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]
CREDENTIALS_PATH = Path("credentials.json")
TOKEN_PATH = Path("token.json")
DEFAULT_RECIPIENTS_PATH = Path("config/recipients.json")

DATA_URI_RE = re.compile(r'src="data:(image/[\w+.-]+);base64,([^"]+)"')


def get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                sys.exit(
                    "credentials.json not found. Download an OAuth client from the "
                    "Google Cloud Console (Gmail API enabled) and place it at the "
                    "project root."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


def load_recipients(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    recipients = data.get("recipients", [])
    if not recipients:
        sys.exit(f"No recipients found in {path}")
    return recipients


def extract_inline_images(html_body: str) -> tuple[str, list[MIMEImage]]:
    """Replace data: URI <img> sources with cid: references and return the
    corresponding MIMEImage parts to attach inline."""
    images: list[MIMEImage] = []

    def replace(match: re.Match) -> str:
        mime_subtype = match.group(1).split("/")[1]
        image_bytes = base64.b64decode(match.group(2))
        cid = uuid.uuid4().hex
        part = MIMEImage(image_bytes, _subtype=mime_subtype)
        part.add_header("Content-ID", f"<{cid}>")
        part.add_header("Content-Disposition", "inline")
        images.append(part)
        return f'src="cid:{cid}"'

    new_html = DATA_URI_RE.sub(replace, html_body)
    return new_html, images


def build_message(html_body: str, subject: str, recipients: list[str]) -> dict:
    html_body, images = extract_inline_images(html_body)

    message = MIMEMultipart("related")
    message["To"] = recipients[0] if len(recipients) == 1 else ""
    message["Bcc"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))
    for image in images:
        message.attach(image)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Gmail draft (or send) with the newsletter HTML")
    parser.add_argument("html_path", help="Path to the final rendered newsletter HTML")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--recipients", default=str(DEFAULT_RECIPIENTS_PATH), help="Path to recipients JSON")
    parser.add_argument("--send", action="store_true", help="Send immediately instead of creating a draft")
    args = parser.parse_args()

    html_body = Path(args.html_path).read_text(encoding="utf-8")
    recipients = load_recipients(Path(args.recipients))

    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)
    message = build_message(html_body, args.subject, recipients)

    if args.send:
        sent = service.users().messages().send(userId="me", body=message).execute()
        print(f"Sent: message id {sent['id']}")
    else:
        draft = service.users().drafts().create(userId="me", body={"message": message}).execute()
        print(f"Draft created: {draft['id']}")
        print("Open Gmail > Drafts to review and send.")


if __name__ == "__main__":
    main()
