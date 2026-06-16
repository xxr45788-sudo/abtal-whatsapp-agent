import os
import re
import threading
import requests
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse

from config import CUSTOMER_IMAGES_FOLDER, BRAND_WHATSAPP_NUMBER
from simple_admin import simple_admin_bp
from services.ai_service import generate_ai_reply
from services.product_service import format_categories_reply, get_product_by_id
from services.whatsapp_service import send_whatsapp_media

from services.image_search_service import (
    find_similar_products_by_image,
    format_image_search_reply
)

from services.order_service import (
    start_order_by_product_name,
    continue_order_session,
    is_order_start_message,
    get_latest_order_for_user
)



app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

app.register_blueprint(simple_admin_bp)



@app.route("/", methods=["GET"])
def home():
    return "ABTAL ALMALAEB WhatsApp AI Agent is running."


@app.route("/test", methods=["GET"])
def test_chat():
    user_message = request.args.get("message", "")

    if not user_message:
        return """
        <h2>ABTAL ALMALAEB AI Agent Test</h2>
        <p>Use this format:</p>
        <p>http://127.0.0.1:5000/test?message=السلام عليكم</p>
        """

    try:
        bot_reply = generate_ai_reply(user_message)
    except Exception as error:
        print("ERROR in /test:", error)
        bot_reply = "صار خطأ بسيط في النظام. جرّب مرة ثانية أو اكتب: المنتجات"

    return f"""
    <h2>ABTAL ALMALAEB AI Agent Test</h2>
    <p><strong>Customer:</strong> {user_message}</p>
    <pre><strong>Bot:</strong>
{bot_reply}</pre>
    """


@app.route("/images/<path:filename>", methods=["GET"])
def serve_image(filename):
    return send_from_directory("images", filename)


@app.route("/orders/generated_pdfs/<path:filename>", methods=["GET"])
def serve_order_pdf(filename):
    return send_from_directory("orders/generated_pdfs", filename)


def get_public_base_url():
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


def extract_first_product_id(text):
    if not text:
        return None

    match = re.search(r"\bP\d{3}\b", text.upper())

    if match:
        return match.group(0)

    return None


def build_public_image_url(image_path):
    public_base_url = get_public_base_url()

    if not public_base_url:
        return None

    filename = image_path.replace("\\", "/").split("/")[-1]
    return f"{public_base_url}/images/{filename}"


def build_public_pdf_url(pdf_path):
    public_base_url = get_public_base_url()

    if not public_base_url:
        return None

    filename = pdf_path.replace("\\", "/").split("/")[-1]
    return f"{public_base_url}/orders/generated_pdfs/{filename}"


def download_twilio_media(media_url, save_folder, filename):
    os.makedirs(save_folder, exist_ok=True)

    file_path = os.path.join(save_folder, filename)

    response = requests.get(media_url, timeout=20)

    if response.status_code != 200:
        raise Exception(f"Failed to download media. Status code: {response.status_code}")

    with open(file_path, "wb") as file:
        file.write(response.content)

    return file_path


def send_product_image_in_background(sender_number, bot_reply):
    try:
        product_id = extract_first_product_id(bot_reply)

        if not product_id:
            return

        product = get_product_by_id(product_id)

        if not product:
            return

        image_path = product.get("image")

        if not image_path:
            return

        media_url = build_public_image_url(image_path)

        if not media_url:
            return

        print("Product image URL:", media_url)

        send_whatsapp_media(
            to_number=sender_number,
            message=f"صورة المنتج: {product.get('name_ar')}",
            media_url=media_url
        )

    except Exception as error:
        print("IMAGE SEND ERROR:", error)


def send_order_pdf_to_shop_in_background(sender_number):
    try:
        latest_order = get_latest_order_for_user(sender_number)

        if not latest_order:
            print("No latest order found for:", sender_number)
            return

        pdf_path = latest_order.get("pdf_path")

        if not pdf_path:
            print("No PDF path found in latest order.")
            return

        pdf_url = build_public_pdf_url(pdf_path)

        if not pdf_url:
            print("PUBLIC_BASE_URL is missing.")
            return

        print("Order PDF URL:", pdf_url)

        send_whatsapp_media(
            to_number=BRAND_WHATSAPP_NUMBER,
            message=(
                "طلب جديد من أبطال الملاعب ✅\n\n"
                f"رقم الطلب: {latest_order.get('order_id')}\n"
                f"العميل: {latest_order.get('customer_name')}\n"
                f"رقم العميل: {latest_order.get('customer_whatsapp')}\n"
                f"المنتج: {latest_order.get('product_name')}\n"
                f"المقاس: {latest_order.get('size')}\n"
                f"اللون: {latest_order.get('color')}\n"
                f"الكمية: {latest_order.get('quantity')}\n"
                f"الإجمالي: {latest_order.get('total_omr')} ريال\n"
                f"الموقع: {latest_order.get('delivery_location')}"
            ),
            media_url=pdf_url
        )

    except Exception as error:
        print("PDF SEND ERROR:", error)


@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    response = MessagingResponse()

    incoming_message = request.form.get("Body", "").strip()
    sender_number = request.form.get("From", "").strip()

    num_media = int(request.form.get("NumMedia", 0))
    media_url = request.form.get("MediaUrl0", "")
    media_type = request.form.get("MediaContentType0", "")

    print("=" * 60)
    print("FROM:", sender_number)
    print("MESSAGE:", incoming_message)
    print("NUM MEDIA:", num_media)
    print("MEDIA TYPE:", media_type)

    try:
        # 1. Image search
        if num_media > 0 and "image" in media_type:
            image_path = download_twilio_media(
                media_url=media_url,
                save_folder=CUSTOMER_IMAGES_FOLDER,
                filename="latest_customer_image.jpg"
            )

            result = find_similar_products_by_image(image_path)
            bot_reply = format_image_search_reply(result)

            response.message(bot_reply)
            return str(response)

        # 2. Continue order BEFORE AI
        order_reply = continue_order_session(sender_number, incoming_message)

        if order_reply:
            print("ORDER REPLY:", order_reply)
            response.message(order_reply)

            if "تم تأكيد طلبك بنجاح" in order_reply:
                threading.Thread(
                    target=send_order_pdf_to_shop_in_background,
                    args=(sender_number,),
                    daemon=True
                ).start()

            return str(response)

        # 3. Start order BEFORE AI
        if is_order_start_message(incoming_message):
            order_reply = start_order_by_product_name(sender_number, incoming_message)
            print("START ORDER REPLY:", order_reply)
            response.message(order_reply)
            return str(response)

        # 4. AI reply only if there is no active order
        if not incoming_message:
            bot_reply = format_categories_reply()
        else:
            bot_reply = generate_ai_reply(incoming_message)

        if not bot_reply:
            bot_reply = (
                "هلا وسهلا فيك في أبطال الملاعب 👋\n"
                "اكتب: المنتجات\n"
                "أو اكتب اسم المنتج الذي تبحث عنه."
            )

        response.message(bot_reply)

        threading.Thread(
            target=send_product_image_in_background,
            args=(sender_number, bot_reply),
            daemon=True
        ).start()

        return str(response)

    except Exception as error:
        print("WHATSAPP ERROR:", error)

        response.message(
            "صار خطأ بسيط في النظام ✅\n"
            "اكتب: أريد أطلب طقم الأرجنتين"
        )

        return str(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

