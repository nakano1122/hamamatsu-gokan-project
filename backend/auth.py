import base64
import hashlib
import hmac
import os

from dotenv import load_dotenv

load_dotenv()

channel_secret = os.environ["LINE_CHANNEL_SECRET"]  # Channel secret string
body = "..."  # Request body string
hash = hmac.new(channel_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
signature = base64.b64encode(hash)
# Compare x-line-signature request header and the signature
