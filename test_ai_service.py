from services.ai_service import generate_ai_reply

test_messages = [
    "السلام عليكم",
    "أريد طقم الأرجنتين",
    "عندكم شي مناسب للتمرين؟",
    "أريد حذاء كرة قدم",
    "كم سعر ريال مدريد؟",
    "P001",
    "أريد أطلب طقم برشلونة مقاس L",
    "do you have Barcelona kit?",
    "I need football shoes"
]

for message in test_messages:
    print("=" * 60)
    print("Customer:", message)
    print("Bot:")
    print(generate_ai_reply(message))
    print()