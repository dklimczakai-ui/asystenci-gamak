"""
Przywraca etykietę INBOX dla maili z biuro.gamak które zostały auto-archived przez pipeline.

Daniel powiedział: biuro tylko do wglądu, żadnej automatyki.
Cofamy auto-archive dla tej skrzynki — wraca INBOX label, status w DDB = CLASSIFIED.
"""
import json
import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

REGION = "eu-central-1"
SECRET_ID = "gmail-oauth-biuro-gamak"
TABLE = "mail-emails"
MAILBOX = "biuro.gamak@gmail.com"

sm = boto3.client("secretsmanager", region_name=REGION)
s = json.loads(sm.get_secret_value(SecretId=SECRET_ID)["SecretString"])
creds = Credentials(
    token=s.get("access_token"),
    refresh_token=s["refresh_token"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=s["client_id"],
    client_secret=s["client_secret"],
    scopes=s.get("scopes", ["https://mail.google.com/"]),
)
service = build("gmail", "v1", credentials=creds, cache_discovery=False)
ddb = boto3.resource("dynamodb", region_name=REGION)
table = ddb.Table(TABLE)

# Wszystkie AUTO_ARCHIVED z biuro
resp = table.scan(
    FilterExpression="mailbox_email = :mb AND #s = :s",
    ExpressionAttributeNames={"#s": "status"},
    ExpressionAttributeValues={":mb": MAILBOX, ":s": "AUTO_ARCHIVED"},
    ProjectionExpression="message_id, received_at, subject",
)
items = resp.get("Items", [])
print(f"Found {len(items)} AUTO_ARCHIVED w biuro do przywrócenia")

restored, failed = 0, 0
for item in items:
    msg_id = item["message_id"]
    subj = item.get("subject", "")[:50]
    try:
        service.users().messages().modify(
            userId="me", id=msg_id, body={"addLabelIds": ["INBOX"]}
        ).execute()
        # Update DDB status z AUTO_ARCHIVED → CLASSIFIED (zostawiamy klasyfikację, cofamy archive)
        table.update_item(
            Key={"message_id": msg_id, "received_at": int(item["received_at"])},
            UpdateExpression="SET #s = :s REMOVE auto_archived_at",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "CLASSIFIED"},
        )
        print(f"  [OK] {msg_id} | {subj}")
        restored += 1
    except Exception as e:
        print(f"  [FAIL] {msg_id} | {subj} | {e}")
        failed += 1

print(f"\nDONE: restored={restored}, failed={failed}")
