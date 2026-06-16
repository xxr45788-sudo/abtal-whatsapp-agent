
import json
import os
import re
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, request, redirect, url_for, session
from werkzeug.utils import secure_filename

from config import ITEMS_FILE, ORDERS_FILE


simple_admin_bp = Blueprint("simple_admin", __name__)

UPLOAD_FOLDER = "images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# ============================================================
# HELPERS
# ============================================================

def slugify(text):
    text = str(text or "").strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\u0600-\u06FF\-]", "", text)
    return text or "item"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(image):
    if not image or not image.filename:
        return ""

    if not allowed_file(image.filename):
        return ""

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    original = secure_filename(image.filename)
    extension = original.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"

    save_path = os.path.join(UPLOAD_FOLDER, filename)
    image.save(save_path)

    return save_path.replace("\\", "/")


def is_admin_logged_in():
    return session.get("admin_logged_in") is True


def require_admin_login():
    if not is_admin_logged_in():
        return redirect(url_for("simple_admin.admin_login"))

    login_time = session.get("login_time")

    if not login_time:
        session.clear()
        return redirect(url_for("simple_admin.admin_login"))

    try:
        login_time = datetime.fromisoformat(login_time)
    except Exception:
        session.clear()
        return redirect(url_for("simple_admin.admin_login"))

   
# تنتهي جلسة الدخول بعد ساعة واحدة للأمان
    if datetime.now() - login_time > timedelta(hours=1):
        session.clear()
        return redirect(url_for("simple_admin.admin_login"))




def load_items_data():
    if not os.path.exists(ITEMS_FILE):
        return {
            "store": {
                "name_ar": "أبطال الملاعب",
                "name_en": "ABTAL ALMALAEB",
                "logo": "images/abtal_logo_transparent.png"
            },
            "categories": [],
            "products": []
        }

    with open(ITEMS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    data.setdefault("store", {})
    data.setdefault("categories", [])
    data.setdefault("products", [])

    return data


def save_items_data(data):
    os.makedirs(os.path.dirname(ITEMS_FILE), exist_ok=True)

    with open(ITEMS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_orders_data():
    if not os.path.exists(ORDERS_FILE):
        return {"orders": []}

    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        data.setdefault("orders", [])
        return data

    except Exception:
        return {"orders": []}


def save_orders_data(data):
    os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)

    with open(ORDERS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_all_orders():
    data = load_orders_data()
    return list(reversed(data.get("orders", [])))


def get_order_by_id(order_id):
    data = load_orders_data()

    for order in data.get("orders", []):
        if order.get("order_id") == order_id:
            return order, data

    return None, data


def count_orders_by_status(orders, status):
    return len([
        order for order in orders
        if order.get("status", "new") == status
    ])


def build_pdf_link(order):
    pdf_path = order.get("pdf_path", "")

    if not pdf_path:
        return "No PDF"

    pdf_path = pdf_path.replace("\\", "/")
    return f'<a class="btn btn-dark" target="_blank" href="/{pdf_path}">Open PDF</a>'


def generate_next_product_id(data):
    max_number = 0

    for product in data.get("products", []):
        product_id = str(product.get("id", ""))

        if product_id.startswith("P"):
            try:
                number = int(product_id.replace("P", ""))
                max_number = max(max_number, number)
            except ValueError:
                pass

    return f"P{max_number + 1:03d}"


def get_category_by_id(data, category_id):
    for category in data.get("categories", []):
        if category.get("id") == category_id:
            return category

    return None


def get_subcategory_by_id(data, category_id, subcategory_id):
    category = get_category_by_id(data, category_id)

    if not category:
        return None

    for subcategory in category.get("subcategories", []):
        if subcategory.get("id") == subcategory_id:
            return subcategory

    return None


def get_product_by_id(data, product_id):
    for product in data.get("products", []):
        if product.get("id") == product_id:
            return product

    return None


def product_uses_category(data, category_id):
    for product in data.get("products", []):
        if product.get("category_id") == category_id:
            return True

    return False


def product_uses_subcategory(data, subcategory_id):
    for product in data.get("products", []):
        if product.get("subcategory_id") == subcategory_id:
            return True

    return False


def parse_attributes_from_form():
    attributes = {}

    keys = request.form.getlist("attribute_key")
    values = request.form.getlist("attribute_value")

    for index, key in enumerate(keys):
        key = key.strip()
        if not key:
            continue

        value = ""
        if index < len(values):
            value = values[index].strip()

        if value:
            attributes[key] = value

    return attributes


def parse_sizes_from_form():
    sizes = []

    size_names = request.form.getlist("size_name")
    size_statuses = request.form.getlist("size_status")

    for index, name in enumerate(size_names):
        name = name.strip()

        if not name:
            continue

        status = "available"

        if index < len(size_statuses):
            status = size_statuses[index].strip() or "available"

        sizes.append({
            "name": name,
            "status": status
        })

    return sizes


def parse_variants_from_form():
    variants = []

    color_ar_list = request.form.getlist("variant_color_ar")
    color_en_list = request.form.getlist("variant_color_en")
    status_list = request.form.getlist("variant_status")
    existing_images = request.form.getlist("variant_existing_image")
    image_files = request.files.getlist("variant_image")

    for index, color_ar in enumerate(color_ar_list):
        color_ar = color_ar.strip()

        if not color_ar:
            continue

        color_en = ""
        status = "available"
        image_path = ""

        if index < len(color_en_list):
            color_en = color_en_list[index].strip()

        if index < len(status_list):
            status = status_list[index].strip() or "available"

        if index < len(existing_images):
            image_path = existing_images[index].strip()

        if index < len(image_files):
            new_image_path = save_uploaded_image(image_files[index])
            if new_image_path:
                image_path = new_image_path

        variants.append({
            "color_ar": color_ar,
            "color_en": color_en,
            "image": image_path,
            "status": status,
            "keywords": []
        })

    return variants


def parse_kit_items_from_form():
    kit_items = []

    names_ar = request.form.getlist("kit_item_name_ar")
    names_en = request.form.getlist("kit_item_name_en")
    statuses = request.form.getlist("kit_item_status")

    for index, name_ar in enumerate(names_ar):
        name_ar = name_ar.strip()

        if not name_ar:
            continue

        name_en = ""
        status = "available"

        if index < len(names_en):
            name_en = names_en[index].strip()

        if index < len(statuses):
            status = statuses[index].strip() or "available"

        kit_items.append({
            "name_ar": name_ar,
            "name_en": name_en,
            "status": status
        })

    return kit_items


def category_options_html(data, selected_id=""):
    html = ""

    for category in data.get("categories", []):
        selected = "selected" if category.get("id") == selected_id else ""
        html += f"""
        <option value="{category.get('id')}" {selected}>
            {category.get('name_ar')} ({category.get('id')})
        </option>
        """

    return html


def subcategory_options_html(data, selected_id=""):
    html = '<option value="">بدون قسم فرعي</option>'

    for category in data.get("categories", []):
        for subcategory in category.get("subcategories", []):
            selected = "selected" if subcategory.get("id") == selected_id else ""
            html += f"""
            <option value="{subcategory.get('id')}" {selected}>
                {category.get('name_ar')} - {subcategory.get('name_ar')}
            </option>
            """

    return html


def product_type_options_html(selected_type=""):
    types = [
        ("shirt", "قميص / تيشيرت"),
        ("pants", "بنطال"),
        ("shorts", "شورت"),
        ("tracksuit", "بدلة رياضية"),
        ("shoes", "حذاء"),
        ("football_shoes", "حذاء كرة قدم"),
        ("accessory", "إكسسوار"),
        ("other", "منتج آخر")
    ]

    html = ""

    for value, label in types:
        selected = "selected" if selected_type == value else ""
        html += f'<option value="{value}" {selected}>{label}</option>'

    return html


# ============================================================
# SPORT DASHBOARD TEMPLATE
# ============================================================

def page_template(title, body):
    data = load_items_data()
    store = data.get("store", {})
    logo = store.get("logo", "images/abtal_logo_transparent.png")
    store_name_ar = store.get("name_ar", "أبطال الملاعب")
    store_name_en = store.get("name_en", "ABTAL ALMALAEB")

    return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>

        <style>
            @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800;900&display=swap');

            :root {{
                --black: #050505;
                --dark: #0a0a0a;
                --white: #ffffff;
                --grass: #17c964;
                --lime: #b6ff3b;
                --orange: #ff6b00;
                --red: #ef233c;
                --blue: #2563eb;
                --bg: #f4f4f0;
                --muted: #707070;
                --line: #e2e2dd;
                --card: rgba(255,255,255,0.94);
                --shadow: 0 24px 70px rgba(0,0,0,0.14);
                --radius-xl: 34px;
                --radius-lg: 24px;
            }}

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                color: var(--black);
                font-family: 'Tajawal', Arial, sans-serif;
                font-size: 15px;
                line-height: 1.7;
                min-height: 100vh;
                background:
                    radial-gradient(circle at 10% 10%, rgba(182,255,59,0.26), transparent 24%),
                    radial-gradient(circle at 90% 16%, rgba(255,107,0,0.16), transparent 26%),
                    linear-gradient(135deg, #f7f7f2 0%, #eeeeea 45%, #f9f9f6 100%);
            }}

            body::before {{
                content: "";
                position: fixed;
                inset: 0;
                pointer-events: none;
                opacity: 0.055;
                background-image:
                    linear-gradient(90deg, #000 1px, transparent 1px),
                    linear-gradient(#000 1px, transparent 1px);
                background-size: 46px 46px;
                z-index: -2;
            }}

            body::after {{
                content: "";
                position: fixed;
                inset: 0;
                pointer-events: none;
                background:
                    linear-gradient(90deg, transparent 0 47%, rgba(23,201,100,0.13) 47% 53%, transparent 53%),
                    radial-gradient(circle at center, transparent 0 105px, rgba(0,0,0,0.08) 106px 108px, transparent 109px);
                opacity: 0.35;
                z-index: -1;
            }}

            .navbar {{
                position: sticky;
                top: 0;
                z-index: 50;
                min-height: 82px;
                padding: 0 42px;
                background: rgba(255,255,255,0.86);
                backdrop-filter: blur(20px);
                border-bottom: 1px solid rgba(0,0,0,0.08);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}

            .brand {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}

            .brand img {{
                width: 58px;
                height: 58px;
                object-fit: contain;
                background: #000;
                border-radius: 50%;
                padding: 6px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.25);
            }}

            .brand-title {{
                font-size: 19px;
                font-weight: 900;
                letter-spacing: -0.7px;
                line-height: 1.1;
            }}

            .brand-subtitle {{
                font-size: 12px;
                color: var(--muted);
                font-weight: 800;
                letter-spacing: 1.7px;
                text-transform: uppercase;
            }}

            .nav-links {{
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }}

            .nav-links a {{
                text-decoration: none;
                color: var(--black);
                font-weight: 900;
                padding: 11px 15px;
                border-radius: 999px;
                transition: 0.18s ease;
                font-size: 14px;
                border: 1px solid transparent;
            }}

            .nav-links a:hover {{
                background: var(--black);
                color: var(--white);
                transform: translateY(-2px) scale(1.02);
                box-shadow: 0 14px 30px rgba(0,0,0,0.20);
            }}

            .container {{
                width: min(1400px, calc(100% - 42px));
                margin: 30px auto 70px;
            }}

            .hero {{
                min-height: 250px;
                background:
                    linear-gradient(135deg, rgba(0,0,0,0.98), rgba(17,17,17,0.92)),
                    radial-gradient(circle at 20% 20%, rgba(182,255,59,0.28), transparent 24%);
                color: white;
                border-radius: var(--radius-xl);
                padding: 42px;
                margin-bottom: 28px;
                box-shadow: var(--shadow);
                position: relative;
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.10);
            }}

            .hero::before {{
                content: "";
                position: absolute;
                inset: 18px;
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 26px;
                pointer-events: none;
            }}

            .hero::after {{
                content: "GAME ON";
                position: absolute;
                left: 24px;
                bottom: -42px;
                font-size: 132px;
                font-weight: 900;
                letter-spacing: -9px;
                color: rgba(255,255,255,0.055);
                direction: ltr;
            }}

            .hero h1 {{
                margin: 0 0 12px;
                color: white;
                font-size: clamp(38px, 5vw, 76px);
                font-weight: 900;
                letter-spacing: -2.5px;
                line-height: 0.95;
                position: relative;
                z-index: 2;
            }}

            .hero p {{
                margin: 0;
                max-width: 780px;
                color: rgba(255,255,255,0.78);
                font-size: 19px;
                font-weight: 600;
                position: relative;
                z-index: 2;
            }}

            .cards {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 18px;
                margin: 24px 0;
            }}

            .card {{
                background: var(--card);
                border: 1px solid rgba(0,0,0,0.08);
                border-radius: var(--radius-lg);
                padding: 25px;
                box-shadow: 0 12px 34px rgba(0,0,0,0.06);
                transition: 0.18s ease;
                position: relative;
                overflow: hidden;
            }}

            .card::after {{
                content: "";
                position: absolute;
                inset: auto -30px -30px auto;
                width: 110px;
                height: 110px;
                border-radius: 50%;
                background: rgba(182,255,59,0.20);
            }}

            .card:hover {{
                transform: translateY(-5px);
                box-shadow: var(--shadow);
            }}

            .card h2 {{
                margin: 0;
                font-size: 48px;
                font-weight: 900;
                letter-spacing: -1.7px;
            }}

            .card h3 {{
                margin-top: 0;
                font-size: 22px;
                font-weight: 900;
            }}

            .card p {{
                margin: 6px 0 0;
                color: var(--muted);
                font-weight: 800;
            }}

            h1, h2, h3 {{
                color: var(--black);
                letter-spacing: -0.7px;
            }}

            table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0 13px;
                margin-top: 22px;
            }}

            th {{
                color: var(--muted);
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.9px;
                padding: 0 18px 4px;
                text-align: right;
                font-weight: 900;
            }}

            td {{
                background: rgba(255,255,255,0.95);
                padding: 18px;
                border-top: 1px solid var(--line);
                border-bottom: 1px solid var(--line);
                vertical-align: middle;
                font-weight: 700;
            }}

            td:first-child {{
                border-right: 1px solid var(--line);
                border-radius: 0 22px 22px 0;
            }}

            td:last-child {{
                border-left: 1px solid var(--line);
                border-radius: 22px 0 0 22px;
            }}

            tr:hover td {{
                background: #ffffff;
                box-shadow: 0 12px 30px rgba(0,0,0,0.05);
            }}

            input, textarea, select {{
                width: 100%;
                padding: 15px 16px;
                margin-top: 8px;
                border: 1px solid #d4d4d4;
                border-radius: 17px;
                background: #fff;
                color: var(--black);
                font-family: 'Tajawal', Arial, sans-serif;
                font-size: 15px;
                font-weight: 700;
                outline: none;
                transition: 0.15s ease;
            }}

            input:focus, textarea:focus, select:focus {{
                border-color: var(--black);
                box-shadow: 0 0 0 4px rgba(182,255,59,0.28);
            }}

            textarea {{
                min-height: 120px;
                resize: vertical;
            }}

            label {{
                display: block;
                font-weight: 900;
                color: var(--black);
                margin-bottom: 4px;
            }}

            .form-grid {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 20px;
                background: rgba(255,255,255,0.94);
                border-radius: var(--radius-xl);
                border: 1px solid rgba(0,0,0,0.08);
                padding: 28px;
                box-shadow: 0 18px 50px rgba(0,0,0,0.08);
            }}

            .full {{
                grid-column: 1 / 3;
            }}

            .mini-box {{
                background:
                    linear-gradient(135deg, #ffffff, #f7f7f0);
                border: 1px solid #e4e4dc;
                padding: 18px;
                border-radius: 22px;
                margin-bottom: 14px;
            }}

            .btn {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                min-height: 45px;
                padding: 11px 18px;
                border-radius: 999px;
                border: 1px solid transparent;
                background: var(--black);
                color: white;
                text-decoration: none;
                cursor: pointer;
                font-family: 'Tajawal', Arial, sans-serif;
                font-size: 14px;
                font-weight: 900;
                margin: 4px;
                transition: 0.18s ease;
                position: relative;
                overflow: hidden;
            }}

            .btn::after {{
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
                transform: translateX(110%);
                transition: 0.35s ease;
            }}

            .btn:hover {{
                transform: translateY(-3px) scale(1.02);
                box-shadow: 0 14px 30px rgba(0,0,0,0.22);
            }}

            .btn:hover::after {{
                transform: translateX(-110%);
            }}

            .btn:active {{
                transform: scale(0.96);
            }}

            .btn-green {{
                background: linear-gradient(135deg, #16a34a, #22c55e);
            }}

            .btn-red {{
                background: linear-gradient(135deg, #dc2626, #ef4444);
            }}

            .btn-gray {{
                background: linear-gradient(135deg, #737373, #525252);
            }}

            .btn-orange {{
                background: linear-gradient(135deg, #ea580c, #ff6b00);
            }}

            .btn-dark {{
                background: linear-gradient(135deg, #000000, #1f1f1f);
            }}

            .status {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 7px 12px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 900;
            }}

            .available, .completed {{
                background: #dcfce7;
                color: #166534;
            }}

            .out_of_stock, .cancelled {{
                background: #fee2e2;
                color: #991b1b;
            }}

            .hidden {{
                background: #e5e5e5;
                color: #404040;
            }}

            .new {{
                background: #fef9c3;
                color: #854d0e;
            }}

            .processing {{
                background: #dbeafe;
                color: #1d4ed8;
            }}

            .small {{
                color: var(--muted);
                font-size: 13px;
                font-weight: 800;
            }}

            img.product-img {{
                width: 90px;
                height: 90px;
                object-fit: cover;
                border-radius: 24px;
                border: 1px solid var(--line);
                background: #f3f3f3;
                box-shadow: 0 12px 26px rgba(0,0,0,0.10);
            }}

            .live-preview {{
                margin-top: 10px;
            }}

            .login-note {{
                background: rgba(182,255,59,0.18);
                border: 1px solid rgba(0,0,0,0.08);
                padding: 14px 18px;
                border-radius: 18px;
                font-weight: 800;
            }}

            @media(max-width: 980px) {{
                .navbar {{
                    padding: 16px 20px;
                    flex-direction: column;
                    align-items: stretch;
                    gap: 14px;
                }}

                .nav-links {{
                    overflow-x: auto;
                    flex-wrap: nowrap;
                    padding-bottom: 4px;
                }}

                .container {{
                    width: min(100% - 24px, 1400px);
                    margin-top: 18px;
                }}

                .cards {{
                    grid-template-columns: repeat(2, 1fr);
                }}

                .form-grid {{
                    grid-template-columns: 1fr;
                }}

                .full {{
                    grid-column: 1;
                }}

                .hero {{
                    padding: 30px;
                }}

                .hero::after {{
                    font-size: 78px;
                    bottom: -18px;
                }}

                table {{
                    display: block;
                    overflow-x: auto;
                    white-space: nowrap;
                }}
            }}

            @media(max-width: 600px) {{
                .cards {{
                    grid-template-columns: 1fr;
                }}

                .hero h1 {{
                    font-size: 38px;
                }}

                td, th {{
                    padding: 12px;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="navbar">
            <div class="brand">
                <img src="/{logo}" alt="Logo">
                <div>
                    <div class="brand-title">{store_name_ar}</div>
                    <div class="brand-subtitle">{store_name_en}</div>
                </div>
            </div>

            <div class="nav-links">
                <a href="/admin">الرئيسية</a>
                <a href="/admin/categories">الأقسام</a>
                <a href="/admin/products">المنتجات</a>
                <a href="/admin/products/add">إضافة منتج</a>
                <a href="/admin/orders">الطلبات</a>
                <a href="/admin/logout">خروج</a>
            </div>
        </div>

        <main class="container">
            {body}
        </main>

        <script>
            let audioContext = null;

            function getAudioContext() {{
                if (!audioContext) {{
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }}
                return audioContext;
            }}

            function playTone(frequency, duration, volume) {{
                try {{
                    const ctx = getAudioContext();
                    const oscillator = ctx.createOscillator();
                    const gain = ctx.createGain();

                    oscillator.type = "sine";
                    oscillator.frequency.value = frequency;

                    gain.gain.setValueAtTime(volume, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

                    oscillator.connect(gain);
                    gain.connect(ctx.destination);

                    oscillator.start();
                    oscillator.stop(ctx.currentTime + duration);
                }} catch (error) {{
                    console.log("Audio blocked until user interaction.");
                }}
            }}

            function playHoverSound() {{
                playTone(520, 0.055, 0.035);
            }}

            function playClickSound() {{
                playTone(220, 0.07, 0.055);
                setTimeout(() => playTone(420, 0.08, 0.045), 55);
            }}

            function attachButtonSounds() {{
                const interactiveItems = document.querySelectorAll(".btn, button, .nav-links a");

                interactiveItems.forEach(item => {{
                    item.addEventListener("mouseenter", playHoverSound);
                    item.addEventListener("click", playClickSound);
                }});
            }}

            function previewImage(input) {{
                const file = input.files && input.files[0];
                if (!file) return;

                const preview = input.parentElement.querySelector(".live-preview");
                if (!preview) return;

                preview.src = URL.createObjectURL(file);
                preview.style.display = "block";
            }}

            function fillDefaultSizesIfEmpty() {{
                const productType = document.getElementById("product_type");
                if (!productType) return;

                const sizeInputs = document.querySelectorAll("input[name='size_name']");
                let hasAnySize = false;

                sizeInputs.forEach(input => {{
                    if (input.value.trim() !== "") {{
                        hasAnySize = true;
                    }}
                }});

                if (hasAnySize) return;

                let sizes = [];

                if (["shirt", "pants", "shorts", "tracksuit"].includes(productType.value)) {{
                    sizes = ["S", "M", "L", "XL", "XXL"];
                }} else if (["shoes", "football_shoes"].includes(productType.value)) {{
                    sizes = ["39", "40", "41", "42", "43", "44", "45", "46"];
                }}

                sizeInputs.forEach((input, index) => {{
                    if (index < sizes.length) {{
                        input.value = sizes[index];
                    }}
                }});
            }}

            document.addEventListener("DOMContentLoaded", attachButtonSounds);
        </script>
    </body>
    </html>
    """


# ============================================================
# LOGIN
# ============================================================

@simple_admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "1234")

    if request.method == "GET":
        return page_template("Login", """
        <div class="hero">
            <h1>تسجيل الدخول</h1>
            <p>لوحة إدارة أبطال الملاعب محمية. الجلسة تنتهي تلقائياً بعد 10 دقائق.</p>
        </div>

        <form method="POST" class="form-grid">
            <div class="full login-note">
                تسجيل الدخول مطلوب لحماية بيانات المنتجات والطلبات.
            </div>

            <div class="full">
                <label>اسم المستخدم</label>
                <input type="text" name="username" required>
            </div>

            <div class="full">
                <label>كلمة المرور</label>
                <input type="password" name="password" required>
            </div>

            <div class="full">
                <button class="btn btn-green" type="submit">دخول آمن</button>
            </div>
        </form>
        """)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if username == admin_username and password == admin_password:
        session.clear()
        session["admin_logged_in"] = True
        session["login_time"] = datetime.now().isoformat()
        session.permanent = False
        return redirect(url_for("simple_admin.admin_home"))

    return page_template("Login Failed", """
    <div class="hero">
        <h1>بيانات الدخول غير صحيحة</h1>
        <p>تحقق من اسم المستخدم وكلمة المرور.</p>
    </div>

    <a class="btn btn-red" href="/admin/login">حاول مرة أخرى</a>
    """)


@simple_admin_bp.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("simple_admin.admin_login"))


# ============================================================
# HOME
# ============================================================

@simple_admin_bp.route("/admin")
def admin_home():
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    products = data.get("products", [])
    categories = data.get("categories", [])
    orders = get_all_orders()

    available = len([p for p in products if p.get("status") == "available"])
    new_orders = count_orders_by_status(orders, "new")

    body = f"""
    <div class="hero">
        <h1>لوحة إدارة أبطال الملاعب</h1>
        <p>نظام رياضي ذكي لإدارة المنتجات، المقاسات، الصور، الطلبات، وحالة كل منتج بدقة.</p>
    </div>

    <div class="cards">
        <div class="card"><h2>{len(categories)}</h2><p>الأقسام</p></div>
        <div class="card"><h2>{len(products)}</h2><p>المنتجات</p></div>
        <div class="card"><h2>{available}</h2><p>منتجات متوفرة</p></div>
        <div class="card"><h2>{new_orders}</h2><p>طلبات جديدة</p></div>
    </div>

    <br>

    <a class="btn btn-green" href="/admin/products/add">إضافة منتج</a>
    <a class="btn btn-dark" href="/admin/categories">إدارة الأقسام</a>
    <a class="btn btn-orange" href="/admin/orders">عرض الطلبات</a>
    """

    return page_template("Admin", body)


# ============================================================
# CATEGORIES
# ============================================================

@simple_admin_bp.route("/admin/categories", methods=["GET", "POST"])
def admin_categories():
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()

    if request.method == "POST":
        name_ar = request.form.get("name_ar", "").strip()
        name_en = request.form.get("name_en", "").strip()
        category_id = slugify(request.form.get("category_id") or name_en or name_ar)

        if name_ar:
            exists = get_category_by_id(data, category_id)
            if not exists:
                data["categories"].append({
                    "id": category_id,
                    "name_ar": name_ar,
                    "name_en": name_en or name_ar,
                    "subcategories": []
                })
                save_items_data(data)

        return redirect(url_for("simple_admin.admin_categories"))

    body = """
    <div class="hero">
        <h1>الأقسام</h1>
        <p>أضف وعدّل واحذف الأقسام الرئيسية والفرعية.</p>
    </div>

    <form method="POST" class="form-grid">
        <div class="full"><h2>إضافة قسم جديد</h2></div>

        <div>
            <label>معرّف القسم</label>
            <input type="text" name="category_id" placeholder="football-shirts">
        </div>

        <div>
            <label>اسم القسم بالعربي</label>
            <input type="text" name="name_ar" required>
        </div>

        <div>
            <label>اسم القسم بالإنجليزي</label>
            <input type="text" name="name_en">
        </div>

        <div class="full">
            <button class="btn btn-green" type="submit">إضافة القسم</button>
        </div>
    </form>

    <table>
        <tr>
            <th>القسم</th>
            <th>المعرّف</th>
            <th>الأقسام الفرعية</th>
            <th>إجراءات</th>
        </tr>
    """

    for category in data.get("categories", []):
        subs = category.get("subcategories", [])
        subs_text = ""

        if subs:
            for subcategory in subs:
                subs_text += f"""
                • {subcategory.get('name_ar')} ({subcategory.get('id')})
                <a class="btn btn-red" href="/admin/categories/{category.get('id')}/subcategories/delete/{subcategory.get('id')}">حذف</a>
                <br>
                """
        else:
            subs_text = "لا توجد"

        body += f"""
        <tr>
            <td>{category.get("name_ar")}<br><span class="small">{category.get("name_en")}</span></td>
            <td>{category.get("id")}</td>
            <td>{subs_text}</td>
            <td>
                <a class="btn" href="/admin/categories/edit/{category.get("id")}">تعديل</a>
                <a class="btn btn-green" href="/admin/categories/{category.get("id")}/subcategories/add">إضافة فرعي</a>
                <a class="btn btn-red" href="/admin/categories/delete/{category.get("id")}">حذف القسم</a>
            </td>
        </tr>
        """

    body += "</table>"

    return page_template("Categories", body)


@simple_admin_bp.route("/admin/categories/edit/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    category = get_category_by_id(data, category_id)

    if not category:
        return page_template("Not Found", "<h1>القسم غير موجود</h1>")

    if request.method == "GET":
        return page_template("Edit Category", f"""
        <div class="hero">
            <h1>تعديل القسم</h1>
            <p>{category.get("name_ar")}</p>
        </div>

        <form method="POST" class="form-grid">
            <div>
                <label>اسم القسم بالعربي</label>
                <input type="text" name="name_ar" value="{category.get("name_ar", "")}" required>
            </div>

            <div>
                <label>اسم القسم بالإنجليزي</label>
                <input type="text" name="name_en" value="{category.get("name_en", "")}">
            </div>

            <div class="full">
                <button class="btn btn-green" type="submit">حفظ</button>
                <a class="btn btn-gray" href="/admin/categories">رجوع</a>
            </div>
        </form>
        """)

    category["name_ar"] = request.form.get("name_ar", "").strip()
    category["name_en"] = request.form.get("name_en", "").strip() or category["name_ar"]

    save_items_data(data)

    return redirect(url_for("simple_admin.admin_categories"))


@simple_admin_bp.route("/admin/categories/delete/<category_id>", methods=["GET", "POST"])
def delete_category(category_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    category = get_category_by_id(data, category_id)

    if not category:
        return page_template("Not Found", "<h1>القسم غير موجود</h1>")

    if product_uses_category(data, category_id):
        return page_template("Cannot Delete", """
        <div class="hero">
            <h1>لا يمكن حذف القسم</h1>
            <p>يوجد منتجات تستخدم هذا القسم. احذف المنتجات أو انقلها لقسم آخر أولاً.</p>
        </div>

        <a class="btn" href="/admin/products">عرض المنتجات</a>
        <a class="btn btn-gray" href="/admin/categories">رجوع</a>
        """)

    if request.method == "GET":
        return page_template("Delete Category", f"""
        <div class="hero">
            <h1>حذف القسم</h1>
            <p>هل تريد حذف هذا القسم؟</p>
        </div>

        <h2>{category.get("name_ar")}</h2>

        <form method="POST">
            <button class="btn btn-red" type="submit">نعم، حذف</button>
            <a class="btn btn-gray" href="/admin/categories">إلغاء</a>
        </form>
        """)

    data["categories"] = [
        item for item in data.get("categories", [])
        if item.get("id") != category_id
    ]

    save_items_data(data)

    return redirect(url_for("simple_admin.admin_categories"))


@simple_admin_bp.route("/admin/categories/<category_id>/subcategories/add", methods=["GET", "POST"])
def add_subcategory(category_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    category = get_category_by_id(data, category_id)

    if not category:
        return page_template("Not Found", "<h1>القسم غير موجود</h1>")

    if request.method == "POST":
        name_ar = request.form.get("name_ar", "").strip()
        name_en = request.form.get("name_en", "").strip()
        subcategory_id = slugify(request.form.get("subcategory_id") or name_en or name_ar)

        if name_ar:
            category.setdefault("subcategories", []).append({
                "id": subcategory_id,
                "name_ar": name_ar,
                "name_en": name_en or name_ar
            })
            save_items_data(data)

        return redirect(url_for("simple_admin.admin_categories"))

    return page_template("Add Subcategory", f"""
    <div class="hero">
        <h1>إضافة قسم فرعي</h1>
        <p>القسم الرئيسي: {category.get("name_ar")}</p>
    </div>

    <form method="POST" class="form-grid">
        <div>
            <label>معرّف القسم الفرعي</label>
            <input type="text" name="subcategory_id" placeholder="national-teams">
        </div>

        <div>
            <label>اسم القسم الفرعي بالعربي</label>
            <input type="text" name="name_ar" required>
        </div>

        <div>
            <label>اسم القسم الفرعي بالإنجليزي</label>
            <input type="text" name="name_en">
        </div>

        <div class="full">
            <button class="btn btn-green" type="submit">إضافة</button>
        </div>
    </form>
    """)


@simple_admin_bp.route("/admin/categories/<category_id>/subcategories/delete/<subcategory_id>", methods=["GET", "POST"])
def delete_subcategory(category_id, subcategory_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    category = get_category_by_id(data, category_id)

    if not category:
        return page_template("Not Found", "<h1>القسم غير موجود</h1>")

    subcategory = get_subcategory_by_id(data, category_id, subcategory_id)

    if not subcategory:
        return page_template("Not Found", "<h1>القسم الفرعي غير موجود</h1>")

    if product_uses_subcategory(data, subcategory_id):
        return page_template("Cannot Delete", """
        <div class="hero">
            <h1>لا يمكن حذف القسم الفرعي</h1>
            <p>يوجد منتجات تستخدم هذا القسم الفرعي. عدّل المنتجات أولاً.</p>
        </div>

        <a class="btn" href="/admin/products">عرض المنتجات</a>
        <a class="btn btn-gray" href="/admin/categories">رجوع</a>
        """)

    if request.method == "GET":
        return page_template("Delete Subcategory", f"""
        <div class="hero">
            <h1>حذف القسم الفرعي</h1>
            <p>هل تريد حذف هذا القسم الفرعي؟</p>
        </div>

        <h2>{subcategory.get("name_ar")}</h2>

        <form method="POST">
            <button class="btn btn-red" type="submit">نعم، حذف</button>
            <a class="btn btn-gray" href="/admin/categories">إلغاء</a>
        </form>
        """)

    category["subcategories"] = [
        item for item in category.get("subcategories", [])
        if item.get("id") != subcategory_id
    ]

    save_items_data(data)

    return redirect(url_for("simple_admin.admin_categories"))


# ============================================================
# PRODUCTS
# ============================================================

@simple_admin_bp.route("/admin/products")
def admin_products():
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    products = data.get("products", [])

    body = """
    <div class="hero">
        <h1>المنتجات</h1>
        <p>إدارة المنتجات، النوع، المقاسات، الألوان والصور.</p>
    </div>

    <a class="btn btn-green" href="/admin/products/add">إضافة منتج</a>

    <table>
        <tr>
            <th>الصورة</th>
            <th>المنتج</th>
            <th>القسم</th>
            <th>النوع</th>
            <th>الخصائص</th>
            <th>السعر</th>
            <th>الحالة</th>
            <th>إجراءات</th>
        </tr>
    """

    for product in products:
        image = ""
        if product.get("variants"):
            image = product["variants"][0].get("image", "")

        image_html = f'<img class="product-img" src="/{image}">' if image else "لا توجد صورة"

        category = get_category_by_id(data, product.get("category_id"))
        subcategory = get_subcategory_by_id(data, product.get("category_id"), product.get("subcategory_id"))

        category_text = ""
        if category:
            category_text += category.get("name_ar", "")
        if subcategory:
            category_text += f"<br><span class='small'>{subcategory.get('name_ar')}</span>"

        status = product.get("status", "available")

        attributes = product.get("attributes", {})
        attributes_text = ""

        if isinstance(attributes, dict):
            attributes_text = "<br>".join([
                f"{key}: {value}" for key, value in attributes.items() if value
            ])

        if not attributes_text:
            attributes_text = "-"

        body += f"""
        <tr>
            <td>{image_html}</td>
            <td>
                <strong>{product.get("name_ar")}</strong><br>
                <span class="small">{product.get("name_en", "")}</span><br>
                <span class="small">{product.get("id")}</span>
            </td>
            <td>{category_text}</td>
            <td>{product.get("product_type", "other")}</td>
            <td>{attributes_text}</td>
            <td>{product.get("price_omr", 0)} ريال</td>
            <td><span class="status {status}">{status}</span></td>
            <td>
                <a class="btn" href="/admin/products/edit/{product.get("id")}">تعديل</a>
                <a class="btn btn-red" href="/admin/products/delete/{product.get("id")}">حذف</a>
            </td>
        </tr>
        """

    body += "</table>"

    return page_template("Products", body)


def product_form_html(data, product=None):
    product = product or {}

    category_options = category_options_html(data, product.get("category_id", ""))
    subcategory_options = subcategory_options_html(data, product.get("subcategory_id", ""))
    product_type_options = product_type_options_html(product.get("product_type", ""))

    attributes = product.get("attributes", {})
    if not isinstance(attributes, dict):
        attributes = {}

    attribute_rows = ""

    for key, value in attributes.items():
        attribute_rows += f"""
        <div class="mini-box">
            <input type="text" name="attribute_key" value="{key}" placeholder="اسم الخاصية مثل season أو brand">
            <input type="text" name="attribute_value" value="{value}" placeholder="القيمة">
        </div>
        """

    for _ in range(5):
        attribute_rows += """
        <div class="mini-box">
            <input type="text" name="attribute_key" placeholder="اسم الخاصية مثل season أو brand أو surface">
            <input type="text" name="attribute_value" placeholder="القيمة مثل 2024/2025 أو Nike أو ترتان">
        </div>
        """

    size_rows = ""

    sizes = product.get("sizes", [])

    for size in sizes:
        name = size.get("name", "") if isinstance(size, dict) else str(size)
        status = size.get("status", "available") if isinstance(size, dict) else "available"

        size_rows += f"""
        <div class="mini-box">
            <input type="text" name="size_name" value="{name}" placeholder="S أو 40">
            <select name="size_status">
                <option value="available" {"selected" if status == "available" else ""}>available</option>
                <option value="out_of_stock" {"selected" if status == "out_of_stock" else ""}>out_of_stock</option>
            </select>
        </div>
        """

    for _ in range(8):
        size_rows += """
        <div class="mini-box">
            <input type="text" name="size_name" placeholder="S أو 40">
            <select name="size_status">
                <option value="available">available</option>
                <option value="out_of_stock">out_of_stock</option>
            </select>
        </div>
        """

    variant_rows = ""

    variants = product.get("variants", [])

    for variant in variants:
        color_ar = variant.get("color_ar", "")
        color_en = variant.get("color_en", "")
        status = variant.get("status", "available")
        image = variant.get("image", "")

        image_preview = f'<img class="product-img" src="/{image}">' if image else "لا توجد صورة"

        variant_rows += f"""
        <div class="mini-box">
            <label>لون / صورة موجودة</label>
            <div>{image_preview}</div>
            <input type="hidden" name="variant_existing_image" value="{image}">
            <input type="text" name="variant_color_ar" value="{color_ar}" placeholder="أبيض وسماوي">
            <input type="text" name="variant_color_en" value="{color_en}" placeholder="White and Sky Blue">
            <select name="variant_status">
                <option value="available" {"selected" if status == "available" else ""}>available</option>
                <option value="out_of_stock" {"selected" if status == "out_of_stock" else ""}>out_of_stock</option>
            </select>
            <img class="product-img live-preview" style="display:none; margin-top:10px;">
            <input type="file" name="variant_image" onchange="previewImage(this)">
        </div>
        """

    for number in range(1, 4):
        variant_rows += f"""
        <div class="mini-box">
            <label>لون جديد {number}</label>
            <input type="hidden" name="variant_existing_image" value="">
            <input type="text" name="variant_color_ar" placeholder="أبيض وسماوي">
            <input type="text" name="variant_color_en" placeholder="White and Sky Blue">
            <select name="variant_status">
                <option value="available">available</option>
                <option value="out_of_stock">out_of_stock</option>
            </select>
            <img class="product-img live-preview" style="display:none; margin-top:10px;">
            <input type="file" name="variant_image" onchange="previewImage(this)">
        </div>
        """

    kit_item_rows = ""

    for item in product.get("kit_items", []):
        kit_item_rows += f"""
        <div class="mini-box">
            <input type="text" name="kit_item_name_ar" value="{item.get("name_ar", "")}" placeholder="طقم احتياطي">
            <input type="text" name="kit_item_name_en" value="{item.get("name_en", "")}" placeholder="Away Kit">
            <select name="kit_item_status">
                <option value="available" {"selected" if item.get("status") == "available" else ""}>available</option>
                <option value="out_of_stock" {"selected" if item.get("status") == "out_of_stock" else ""}>out_of_stock</option>
            </select>
        </div>
        """

    for _ in range(2):
        kit_item_rows += """
        <div class="mini-box">
            <input type="text" name="kit_item_name_ar" placeholder="طقم احتياطي">
            <input type="text" name="kit_item_name_en" placeholder="Away Kit">
            <select name="kit_item_status">
                <option value="available">available</option>
                <option value="out_of_stock">out_of_stock</option>
            </select>
        </div>
        """

    keywords_text = ", ".join(product.get("keywords", [])) if isinstance(product.get("keywords"), list) else ""

    return f"""
    <div class="form-grid">

        <div>
            <label>القسم الرئيسي</label>
            <select name="category_id" required>
                {category_options}
            </select>
        </div>

        <div>
            <label>القسم الفرعي</label>
            <select name="subcategory_id">
                {subcategory_options}
            </select>
        </div>

        <div>
            <label>نوع المنتج</label>
            <select name="product_type" id="product_type" onchange="fillDefaultSizesIfEmpty()">
                {product_type_options}
            </select>
        </div>

        <div>
            <label>اسم المنتج بالعربي</label>
            <input type="text" name="name_ar" value="{product.get("name_ar", "")}" required>
        </div>

        <div>
            <label>اسم المنتج بالإنجليزي</label>
            <input type="text" name="name_en" value="{product.get("name_en", "")}">
        </div>

        <div>
            <label>السعر بالريال</label>
            <input type="number" step="0.01" name="price_omr" value="{product.get("price_omr", "")}" required>
        </div>

        <div>
            <label>الحالة العامة للمنتج</label>
            <select name="status">
                <option value="available" {"selected" if product.get("status", "available") == "available" else ""}>available</option>
                <option value="out_of_stock" {"selected" if product.get("status") == "out_of_stock" else ""}>out_of_stock</option>
                <option value="hidden" {"selected" if product.get("status") == "hidden" else ""}>hidden</option>
            </select>
        </div>

        <div class="full">
            <label>الوصف بالعربي</label>
            <textarea name="description_ar">{product.get("description_ar", "")}</textarea>
        </div>

        <div class="full">
            <label>الوصف بالإنجليزي</label>
            <textarea name="description_en">{product.get("description_en", "")}</textarea>
        </div>

        <div class="full">
            <label>كلمات البحث</label>
            <input type="text" name="keywords" value="{keywords_text}" placeholder="الأرجنتين, ميسي, argentina, messi">
        </div>

        <div class="full">
            <h2>خصائص المنتج المرنة</h2>
            <p class="small">
                للأقمصة: team = الأرجنتين, season = 2024/2025, version = Fan Version
                <br>
                للأحذية: brand = Nike, surface = ترتان, stud_type = TF
            </p>
            {attribute_rows}
        </div>

        <div class="full">
            <h2>المقاسات وحالة كل مقاس</h2>
            <p class="small">اختر نوع المنتج أولاً ليتم تعبئة مقاسات افتراضية إذا كانت الخانات فارغة.</p>
            {size_rows}
        </div>

        <div class="full">
            <h2>الألوان / الصور</h2>
            <p class="small">بعد رفع الصورة ستظهر معاينة مباشرة قبل الحفظ.</p>
            {variant_rows}
        </div>

        <div class="full">
            <h2>قطع إضافية اختيارية داخل الطقم</h2>
            <p class="small">استخدمها فقط إذا المنتج يحتوي على طقم أساسي + احتياطي أو قطع إضافية.</p>
            {kit_item_rows}
        </div>

        <div class="full">
            <button class="btn btn-green" type="submit">حفظ</button>
            <a class="btn btn-gray" href="/admin/products">إلغاء</a>
        </div>

    </div>
    """


@simple_admin_bp.route("/admin/products/add", methods=["GET", "POST"])
def add_product():
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()

    if not data.get("categories"):
        return page_template("No Categories", """
        <div class="hero">
            <h1>لا توجد أقسام</h1>
            <p>أضف قسم أولاً قبل إضافة المنتجات.</p>
        </div>

        <a class="btn btn-green" href="/admin/categories">إضافة قسم</a>
        """)

    if request.method == "GET":
        form_html = product_form_html(data)
        return page_template("Add Product", f"""
        <div class="hero">
            <h1>إضافة منتج</h1>
            <p>أضف المنتج مع نوعه، مقاساته، صوره وحالة كل مقاس.</p>
        </div>

        <form method="POST" enctype="multipart/form-data">
            {form_html}
        </form>
        """)

    product_id = generate_next_product_id(data)

    keywords = [
        item.strip()
        for item in request.form.get("keywords", "").split(",")
        if item.strip()
    ]

    try:
        price_omr = float(request.form.get("price_omr", 0))
    except ValueError:
        price_omr = 0.0

    product = {
        "id": product_id,
        "name_ar": request.form.get("name_ar", "").strip(),
        "name_en": request.form.get("name_en", "").strip(),
        "category_id": request.form.get("category_id", "").strip(),
        "subcategory_id": request.form.get("subcategory_id", "").strip(),
        "product_type": request.form.get("product_type", "other").strip(),
        "price_omr": price_omr,
        "description_ar": request.form.get("description_ar", "").strip(),
        "description_en": request.form.get("description_en", "").strip(),
        "status": request.form.get("status", "available").strip(),
        "attributes": parse_attributes_from_form(),
        "sizes": parse_sizes_from_form(),
        "variants": parse_variants_from_form(),
        "kit_items": parse_kit_items_from_form(),
        "keywords": keywords,
        "offer": ""
    }

    data["products"].append(product)
    save_items_data(data)

    return redirect(url_for("simple_admin.admin_products"))


@simple_admin_bp.route("/admin/products/edit/<product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    product = get_product_by_id(data, product_id)

    if not product:
        return page_template("Not Found", "<h1>المنتج غير موجود</h1>")

    if request.method == "GET":
        form_html = product_form_html(data, product)

        return page_template("Edit Product", f"""
        <div class="hero">
            <h1>تعديل المنتج</h1>
            <p>{product.get("name_ar")} - {product.get("id")}</p>
        </div>

        <form method="POST" enctype="multipart/form-data">
            {form_html}
        </form>
        """)

    keywords = [
        item.strip()
        for item in request.form.get("keywords", "").split(",")
        if item.strip()
    ]

    try:
        price_omr = float(request.form.get("price_omr", 0))
    except ValueError:
        price_omr = 0.0

    product["name_ar"] = request.form.get("name_ar", "").strip()
    product["name_en"] = request.form.get("name_en", "").strip()
    product["category_id"] = request.form.get("category_id", "").strip()
    product["subcategory_id"] = request.form.get("subcategory_id", "").strip()
    product["product_type"] = request.form.get("product_type", "other").strip()
    product["price_omr"] = price_omr
    product["description_ar"] = request.form.get("description_ar", "").strip()
    product["description_en"] = request.form.get("description_en", "").strip()
    product["status"] = request.form.get("status", "available").strip()
    product["attributes"] = parse_attributes_from_form()
    product["sizes"] = parse_sizes_from_form()
    product["variants"] = parse_variants_from_form()
    product["kit_items"] = parse_kit_items_from_form()
    product["keywords"] = keywords

    save_items_data(data)

    return redirect(url_for("simple_admin.admin_products"))


@simple_admin_bp.route("/admin/products/delete/<product_id>", methods=["GET", "POST"])
def delete_product(product_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    data = load_items_data()
    product = get_product_by_id(data, product_id)

    if not product:
        return page_template("Not Found", "<h1>المنتج غير موجود</h1>")

    if request.method == "GET":
        return page_template("Delete Product", f"""
        <div class="hero">
            <h1>حذف المنتج</h1>
            <p>هل تريد حذف هذا المنتج؟</p>
        </div>

        <h2>{product.get("name_ar")}</h2>

        <form method="POST">
            <button class="btn btn-red" type="submit">نعم، حذف</button>
            <a class="btn btn-gray" href="/admin/products">إلغاء</a>
        </form>
        """)

    data["products"] = [
        item for item in data.get("products", [])
        if item.get("id") != product_id
    ]

    save_items_data(data)

    return redirect(url_for("simple_admin.admin_products"))


# ============================================================
# ORDERS
# ============================================================

@simple_admin_bp.route("/admin/orders")
def admin_orders():
    login_check = require_admin_login()
    if login_check:
        return login_check

    orders = get_all_orders()

    body = """
    <div class="hero">
        <h1>الطلبات</h1>
        <p>متابعة طلبات العملاء وتغيير حالة كل طلب.</p>
    </div>

    <table>
        <tr>
            <th>رقم الطلب</th>
            <th>العميل</th>
            <th>المنتج</th>
            <th>الإجمالي</th>
            <th>الحالة</th>
            <th>PDF</th>
            <th>إجراءات</th>
        </tr>
    """

    if not orders:
        body += "<tr><td colspan='7'>لا توجد طلبات حالياً.</td></tr>"

    for order in orders:
        status = order.get("status", "new")
        pdf_html = build_pdf_link(order)

        body += f"""
        <tr>
            <td>{order.get("order_id")}</td>
            <td>{order.get("customer_name")}<br><span class="small">{order.get("customer_whatsapp")}</span></td>
            <td>{order.get("product_name")}</td>
            <td>{order.get("total_omr")} ريال</td>
            <td>
                <form method="POST" action="/admin/orders/{order.get("order_id")}/status">
                    <select name="status">
                        <option value="new" {"selected" if status == "new" else ""}>new</option>
                        <option value="processing" {"selected" if status == "processing" else ""}>processing</option>
                        <option value="completed" {"selected" if status == "completed" else ""}>completed</option>
                        <option value="cancelled" {"selected" if status == "cancelled" else ""}>cancelled</option>
                    </select>
                    <button class="btn" type="submit">حفظ</button>
                </form>
            </td>
            <td>{pdf_html}</td>
            <td><a class="btn" href="/admin/orders/{order.get("order_id")}">تفاصيل</a></td>
        </tr>
        """

    body += "</table>"

    return page_template("Orders", body)


@simple_admin_bp.route("/admin/orders/<order_id>/status", methods=["POST"])
def update_order_status(order_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    new_status = request.form.get("status", "new").strip()

    allowed_statuses = [
        "new",
        "processing",
        "completed",
        "cancelled"
    ]

    if new_status not in allowed_statuses:
        new_status = "new"

    order, data = get_order_by_id(order_id)

    if not order:
        return page_template("Not Found", "<h1>الطلب غير موجود</h1>")

    order["status"] = new_status
    save_orders_data(data)

    return redirect(url_for("simple_admin.admin_orders"))


@simple_admin_bp.route("/admin/orders/<order_id>")
def admin_order_details(order_id):
    login_check = require_admin_login()
    if login_check:
        return login_check

    order, data = get_order_by_id(order_id)

    if not order:
        return page_template("Not Found", "<h1>الطلب غير موجود</h1>")

    body = f"""
    <div class="hero">
        <h1>تفاصيل الطلب</h1>
        <p>{order.get("order_id")}</p>
    </div>

    <table>
        <tr><th>الحقل</th><th>القيمة</th></tr>
        <tr><td>العميل</td><td>{order.get("customer_name")}</td></tr>
        <tr><td>الرقم</td><td>{order.get("customer_whatsapp")}</td></tr>
        <tr><td>المنتج</td><td>{order.get("product_name")}</td></tr>
        <tr><td>المقاس</td><td>{order.get("size")}</td></tr>
        <tr><td>اللون</td><td>{order.get("color")}</td></tr>
        <tr><td>الكمية</td><td>{order.get("quantity")}</td></tr>
        <tr><td>الموقع</td><td>{order.get("delivery_location")}</td></tr>
        <tr><td>الإجمالي</td><td>{order.get("total_omr")} ريال</td></tr>
        <tr><td>الحالة</td><td>{order.get("status", "new")}</td></tr>
        <tr><td>PDF</td><td>{build_pdf_link(order)}</td></tr>
    </table>

    <br>
    <a class="btn btn-gray" href="/admin/orders">رجوع</a>
    """

    return page_template("Order Details", body)

