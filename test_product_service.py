from services.product_service import (
    format_categories_reply,
    get_products_by_category,
    format_products_reply,
    search_products,
    get_product_by_id,
    format_single_product_reply,
    get_category_by_user_choice
)

print("=== Categories Reply ===")
print(format_categories_reply())

print("\n=== Products in C001 ===")
products = get_products_by_category("C001")
print(format_products_reply(products))

print("\n=== Search: argentina ===")
results = search_products("argentina")
print(format_products_reply(results))

print("\n=== Product P001 ===")
product = get_product_by_id("P001")
print(format_single_product_reply(product))

print("\n=== Category Choice Test ===")
message = "أريد أشوف الأطقم"
category_id = get_category_by_user_choice(message)
print("Detected category:", category_id)