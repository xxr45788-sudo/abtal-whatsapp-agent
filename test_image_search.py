from services.image_search_service import (
    find_similar_products_by_image,
    format_image_search_reply
)

image_path = "test_customer_image.jpg"
result = find_similar_products_by_image(image_path)

print("AI image keywords:")
print(result["image_keywords"])

print("\nMatched products:")
for item in result["matches"]:
    product = item["product"]
    score = item["score"]
    print(f"- {product['name_ar']} | Score: {score}")

print("\nBot reply:")
print(format_image_search_reply(result))