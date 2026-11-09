import os
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com"   # sandbox = fake money
PAYPAL_CLIENT_ID = os.environ["PAYPAL_CLIENT_ID"]
PAYPAL_CLIENT_SECRET = os.environ["PAYPAL_CLIENT_SECRET"]

# Vendors we trust: name -> the payee email on file
TRUSTED_VENDORS = {"Acme Supplies": os.environ["TRUSTED_VENDOR_EMAIL"]}

MAX_SINGLE_PAYMENT = Decimal("1000")    # above this: always blocked
APPROVAL_THRESHOLD = Decimal("200")     # above this: a human must approve

ADMIN_TOKEN = os.environ['ADMIN_TOKEN']
DB_PATH = "guard.db"

GROQ_API_KEY = os.getenv('GROQ_API_KEY', "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")