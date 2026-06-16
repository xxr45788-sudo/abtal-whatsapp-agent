import os
import sqlite3


DATABASE_FILE = "data/shop_database.db"


def get_connection():
    """
    Create and return a database connection.
    """
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row

    return conn


def init_database():
    """
    Create all required database tables.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ==========================
    # Products table
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            category_id TEXT NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT,
            description_ar TEXT,
            description_en TEXT,
            price_omr REAL NOT NULL,
            image_path TEXT,
            status TEXT DEFAULT 'available',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==========================
    # Product sizes table
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_sizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL,
            size TEXT NOT NULL,
            FOREIGN KEY (product_code) REFERENCES products(code)
        )
    """)

    # ==========================
    # Product colors table
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_colors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL,
            color TEXT NOT NULL,
            FOREIGN KEY (product_code) REFERENCES products(code)
        )
    """)

    # ==========================
    # Orders table
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            customer_whatsapp TEXT,
            customer_name TEXT,
            delivery_location TEXT,

            product_code TEXT,
            product_name TEXT,
            size TEXT,
            color TEXT,
            quantity INTEGER,
            price_omr REAL,
            total_omr REAL,

            notes TEXT,
            pdf_path TEXT,
            status TEXT DEFAULT 'new',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==========================
    # Order sessions table
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_sessions (
            customer_whatsapp TEXT PRIMARY KEY,
            session_data TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==========================
    # Admin users table
    # ==========================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def generate_product_code():
    """
    Generate next product code like P001, P002, P003.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code
        FROM products
        WHERE code LIKE 'P%'
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        return "P001"

    last_code = row["code"]

    try:
        number = int(last_code.replace("P", ""))
        return f"P{number + 1:03d}"
    except ValueError:
        return "P001"


def create_default_admin():
    """
    Create default admin user.
    Later we can improve this with hashed passwords.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM admin_users
        WHERE username = ?
    """, ("admin",))

    existing_admin = cursor.fetchone()

    if not existing_admin:
        cursor.execute("""
            INSERT INTO admin_users (username, password)
            VALUES (?, ?)
        """, ("admin", "1234"))

        print("Default admin created:")
        print("Username: admin")
        print("Password: 1234")

    conn.commit()
    conn.close()


def seed_sample_product_if_empty():
    """
    Add one sample product only if database is empty.
    This helps us test the admin/database system.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM products")
    result = cursor.fetchone()

    if result["count"] == 0:
        product_code = "P001"

        cursor.execute("""
            INSERT INTO products (
                code,
                category_id,
                name_ar,
                name_en,
                description_ar,
                description_en,
                price_omr,
                image_path,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_code,
            "C001",
            "طقم المنتخب الأرجنتيني",
            "Argentina National Team Kit",
            "طقم رياضي للمنتخب الأرجنتيني مناسب للتمارين والمباريات.",
            "Argentina national team sports kit suitable for training and matches.",
            8.5,
            "images/argentina_national_team_kit.webp",
            "available"
        ))

        sample_sizes = ["S", "M", "L", "XL", "XXL"]
        sample_colors = ["أبيض وسماوي"]

        for size in sample_sizes:
            cursor.execute("""
                INSERT INTO product_sizes (product_code, size)
                VALUES (?, ?)
            """, (product_code, size))

        for color in sample_colors:
            cursor.execute("""
                INSERT INTO product_colors (product_code, color)
                VALUES (?, ?)
            """, (product_code, color))

        print("Sample product added: P001")

    conn.commit()
    conn.close()


def reset_database():
    """
    Dangerous: deletes all database tables and recreates them.
    Use only if you want a fresh database.
    """
    if os.path.exists(DATABASE_FILE):
        os.remove(DATABASE_FILE)

    init_database()
    create_default_admin()
    seed_sample_product_if_empty()

    print("Database reset successfully.")


if __name__ == "__main__":
    init_database()
    create_default_admin()
    seed_sample_product_if_empty()

    print("Database created successfully.")
    print(f"Database file: {DATABASE_FILE}")