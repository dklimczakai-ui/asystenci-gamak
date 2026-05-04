"""
Cleanup biuro.gamak z całego pipeline:
1. Usuń draft Gmail (biuro) — ten 1 PENDING dla Galisz/Chrzanów
2. Update DDB → CANCELLED_READONLY_MAILBOX
3. Sprawdź i odepnij Gmail watch (Pub/Sub) z biuro
"""
import json
import boto3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

REGION = "eu-central-1"
SECRET_ID = "gmail-oauth-biuro-gamak"
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
drafts = ddb.Table("mail-drafts")

# 1. PENDING drafty z biuro
resp = drafts.scan(
    FilterExpression="mailbox_email = :mb AND #s = :s",
    ExpressionAttributeNames={"#s": "status"},
    ExpressionAttributeValues={":mb": MAILBOX, ":s": "PENDING"},
)
items = resp.get("Items", [])
print(f"Found {len(items)} PENDING drafts dla biuro do usunięcia")

for item in items:
    draft_id = item["draft_id"]
    gmail_id = item.get("gmail_draft_id", "")
    subj = item.get("subject_reply", "")[:60]
    if gmail_id:
        try:
            service.users().drafts().delete(userId="me", id=gmail_id).execute()
            print(f"  [Gmail OK] deleted draft {gmail_id}")
        except Exception as e:
            print(f"  [Gmail FAIL] {gmail_id}: {e}")
    drafts.update_item(
        Key={"draft_id": draft_id, "created_at": int(item["created_at"])},
        UpdateExpression="SET #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "CANCELLED_READONLY_MAILBOX"},
    )
    print(f"  [DDB OK] {draft_id} | {subj}")

# 2. Sprawdź czy biuro ma Gmail watch (Pub/Sub trigger)
profile = service.users().getProfile(userId="me").execute()
print(f"\nGmail profile: {profile.get('emailAddress')}, historyId: {profile.get('historyId')}")
try:
    # Stop watch
    service.users().stop(userId="me").execute()
    print(f"  [STOP OK] Gmail watch dla {MAILBOX} odpięty (Pub/Sub push wyłączony)")
except Exception as e:
    print(f"  [STOP info] watch stop: {e}")

print("\nDONE: biuro pipeline cleanup")
