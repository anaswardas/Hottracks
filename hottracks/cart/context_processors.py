from .models import Cart

def cart_item_count(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items_count = cart.items.count()
        print(f"Cart Items Count: {cart_items_count}")  
        return {'cart_items_count': cart_items_count}
    return {'cart_items_count': 0}