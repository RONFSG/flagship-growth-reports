#!/usr/bin/env python3
"""Replace the content of ONE existing Google Slides file with a freshly built .pptx, so the link never changes.
Usage: upload_slides.py <service-account.json> <slides_file_id> <deck.pptx> [new title]
The Slides file must be shared with the service account's email as Editor.
Needs network access to oauth2.googleapis.com and www.googleapis.com."""
import json, sys, requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

KEY, FID, PPTX = sys.argv[1:4]
TITLE = sys.argv[4] if len(sys.argv) > 4 else None
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

creds = service_account.Credentials.from_service_account_file(KEY, scopes=["https://www.googleapis.com/auth/drive"])
creds.refresh(Request())
H = {"Authorization": f"Bearer {creds.token}"}

meta = {"name": TITLE} if TITLE else {}
boundary = "fsgdeckboundary"
body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
        f"--{boundary}\r\nContent-Type: {PPTX_MIME}\r\n\r\n").encode() + open(PPTX, "rb").read() + f"\r\n--{boundary}--".encode()
r = requests.patch(f"https://www.googleapis.com/upload/drive/v3/files/{FID}",
                   params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": "id,name,mimeType,modifiedTime,webViewLink"},
                   headers={**H, "Content-Type": f"multipart/related; boundary={boundary}"}, data=body, timeout=120)
if r.status_code != 200:
    sys.exit(f"UPLOAD_FAILED {r.status_code}: {r.text[:500]}")
out = r.json()
if out.get("mimeType") != "application/vnd.google-apps.presentation":
    sys.exit(f"UPLOAD_FAILED: file is no longer Google Slides ({out.get('mimeType')})")
print("UPLOAD_OK", json.dumps(out))
