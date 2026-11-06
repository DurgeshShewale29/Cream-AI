product = "Cream-AI"
about = "Matches a Maharashtra engineering student to the state (MahaDBT) and central (NSP/AICTE) scholarships they qualify for, with amounts, income limits and deadlines."
sample_questions = [
    "I am OBC with Rs 3.2 lakh income. Which scholarship fits me?",
    "What is the difference between EBC and OBC Freeship?",
    "Which documents do I need for MahaDBT?",
    "Is there an AICTE or NSP scholarship I can apply for?",
    "What is the last date to apply this year?",
]
min_value = 60


def show_menu():
    print()
    print(f"--- {product} ---")
    print("1. About the product")
    print("2. Sample questions")
    print("3. Check eligibility")
    print("0. Exit")


while True:
    show_menu()
    choice = input("Choose an option: ").strip()

    if choice == "1":
        print(about)
    elif choice == "2":
        for number, q in enumerate(sample_questions, start=1):
            print(f"{number}. {q}")
    elif choice == "3":
        try:
            value = float(input("Enter your value: "))
        except ValueError:
            print("Please enter a number.")
            continue
        if value >= min_value:
            print(f"Eligible (needs {min_value} or more).")
        else:
            print(f"Not eligible (needs {min_value} or more).")
    elif choice == "0":
        print("Goodbye!")
        break
    else:
        print("Invalid choice, try again.")