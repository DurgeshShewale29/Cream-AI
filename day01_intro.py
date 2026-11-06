product = "Cream-AI"
user = "Maharashtra engineering students (reserved and EWS categories)"
problem = "Students apply for the scheme they know, not the one meant for them."


print("=" * 50)
print("PROJECT CARD")
print("=" * 50)
print(f"Product : {product}")
print(f"User    : {user}")
print(f"Problem : {problem}")
print("=" * 50)

name = input("What is your name? ").strip()
question = input("What is your question? ").strip()

print()
print(f"Hello, {name.title()}!")
print(f"You asked: '{question}' ({len(question)} characters)")
print(f"{product} will be able to answer this in the coming days.")