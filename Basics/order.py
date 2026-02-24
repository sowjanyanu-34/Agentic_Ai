orders = []
while True:
    order = {}
    # User details
    order["name"] = input("\nEnter your name: ")
    order["email"] = input("Enter your email: ")
    order["phone"] = input("Enter your phone: ")
    order["payment"] = input("Enter payment method: ")
    cart = []
    total = 0
    # Cart loop
    while True:
        print("\nItem Name:")
        item = input()
        print("Price:")
        price = float(input())
        cart_item = {
            "item": item,
            "price": price
        }
        cart.append(cart_item)
        total += price
        choice = input("Continue adding items? (yes/no): ")
        if choice.lower() == "no":
            break
    # Store cart and total inside order
    order["cart"] = cart
    order["total"] = total
    orders.append(order)
    print("\n Order Confirmed!")
    print("Total amount:", total)
    again = input("Do you want to purchase again? (yes/no): ")
    if again.lower() == "no":
        break
print("\nAll Orders:")
for o in orders:
    print(o)