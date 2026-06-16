import os

from flask import Blueprint, request, redirect, url_for
from werkzeug.utils import secure_filename

from services.database_product_service import (
    add_product_to_database,
    get_all_database_products,
    update_product_status
)


admin_bp = Blueprint("admin", __name__)


UPLOAD_FOLDER = "images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@admin_bp.route("/admin", methods=["GET"])
def admin_home():
    return """
    <h1>ABTAL ALMALAEB Admin Dashboard</h1>

    <ul>
        <li><a href="/admin/products">View Products</a></li>
        <li><a href="/admin/products/add">Add Product</a></li>
    </ul>
    """


@admin_bp.route("/admin/products", methods=["GET"])
def admin_products():
    products = get_all_database_products()

    html = """
    <h1>Products</h1>
    <p><a href="/admin/products/add">Add New Product</a></p>

    <table border="1" cellpadding="8" cellspacing="0">
        <tr>
            <th>Code</th>
            <th>Name Arabic</th>
            <th>Category</th>
            <th>Price</th>
            <th>Status</th>
            <th>Image</th>
            <th>Actions</th>
        </tr>
    """

    for product in products:
        image_path = product["image_path"] or ""

        if image_path:
            image_html = f'<img src="/{image_path}" width="80">'
        else:
            image_html = "No image"

        html += f"""
        <tr>
            <td>{product["code"]}</td>
            <td>{product["name_ar"]}</td>
            <td>{product["category_id"]}</td>
            <td>{product["price_omr"]} OMR</td>
            <td>{product["status"]}</td>
            <td>{image_html}</td>
            <td>
                <form method="POST" action="/admin/products/status" style="display:inline;">
                    <input type="hidden" name="product_code" value="{product["code"]}">
                    <select name="status">
                        <option value="available">available</option>
                        <option value="out_of_stock">out_of_stock</option>
                        <option value="hidden">hidden</option>
                    </select>
                    <button type="submit">Update Status</button>
                </form>
            </td>
        </tr>
        """

    html += """
    </table>
    <p><a href="/admin">Back to Admin</a></p>
    """

    return html


@admin_bp.route("/admin/products/add", methods=["GET", "POST"])
def add_product_page():
    if request.method == "GET":
        return """
        <h1>Add Product</h1>

        <form method="POST" enctype="multipart/form-data">
            <label>Category ID:</label><br>
            <input type="text" name="category_id" value="C001" required><br><br>

            <label>Arabic Name:</label><br>
            <input type="text" name="name_ar" required><br><br>

            <label>English Name:</label><br>
            <input type="text" name="name_en"><br><br>

            <label>Arabic Description:</label><br>
            <textarea name="description_ar"></textarea><br><br>

            <label>English Description:</label><br>
            <textarea name="description_en"></textarea><br><br>

            <label>Price OMR:</label><br>
            <input type="number" step="0.01" name="price_omr" required><br><br>

            <label>Sizes, separated by comma:</label><br>
            <input type="text" name="sizes" placeholder="S,M,L,XL"><br><br>

            <label>Colors, separated by comma:</label><br>
            <input type="text" name="colors" placeholder="أبيض,أسود"><br><br>

            <label>Status:</label><br>
            <select name="status">
                <option value="available">available</option>
                <option value="out_of_stock">out_of_stock</option>
                <option value="hidden">hidden</option>
            </select><br><br>

            <label>Product Image:</label><br>
            <input type="file" name="image"><br><br>

            <button type="submit">Add Product</button>
        </form>

        <p><a href="/admin/products">Back to Products</a></p>
        """

    category_id = request.form.get("category_id", "").strip()
    name_ar = request.form.get("name_ar", "").strip()
    name_en = request.form.get("name_en", "").strip()
    description_ar = request.form.get("description_ar", "").strip()
    description_en = request.form.get("description_en", "").strip()
    price_omr = float(request.form.get("price_omr", 0))
    sizes_text = request.form.get("sizes", "").strip()
    colors_text = request.form.get("colors", "").strip()
    status = request.form.get("status", "available").strip()

    sizes = [size.strip() for size in sizes_text.split(",") if size.strip()]
    colors = [color.strip() for color in colors_text.split(",") if color.strip()]

    image_path = ""

    image = request.files.get("image")

    if image and image.filename and allowed_file(image.filename):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        filename = secure_filename(image.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)

        image.save(save_path)

        image_path = save_path.replace("\\", "/")

    product_code = add_product_to_database(
        category_id=category_id,
        name_ar=name_ar,
        name_en=name_en,
        description_ar=description_ar,
        description_en=description_en,
        price_omr=price_omr,
        image_path=image_path,
        sizes=sizes,
        colors=colors,
        status=status
    )

    return f"""
    <h1>Product Added Successfully ✅</h1>
    <p>Product Code: <strong>{product_code}</strong></p>
    <p><a href="/admin/products">View Products</a></p>
    <p><a href="/admin/products/add">Add Another Product</a></p>
    """


@admin_bp.route("/admin/products/status", methods=["POST"])
def change_product_status():
    product_code = request.form.get("product_code", "").strip()
    status = request.form.get("status", "").strip()

    update_product_status(product_code, status)

    return redirect(url_for("admin.admin_products"))