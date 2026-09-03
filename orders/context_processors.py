from .cart import Cart


def cart(request):
    """Makes the current cart's item count available to all templates."""
    try:
        return {'cart_item_count': len(Cart(request))}
    except Exception:
        return {'cart_item_count': 0}
