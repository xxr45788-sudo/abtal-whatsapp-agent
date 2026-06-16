import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

BRAND_WHATSAPP_NUMBER = "whatsapp:+96877302888"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
BRAND_FILE = "data/brand_data.json"
ITEMS_FILE = "data/items_data.json"
ORDERS_FOLDER = "orders/generated_pdfs"
CUSTOMER_IMAGES_FOLDER = "customer_images"
ORDERS_FILE = "data/orders_data.json"
ORDER_SESSIONS_FILE = "data/order_sessions.json"