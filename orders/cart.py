from decimal import Decimal
from catalog.models import Product

CART_SESSION_KEY = 'cart'


class Cart:
    """A simple session-backed shopping cart.

    Structure stored in session:
        { "<product_id>": {"quantity": int, "price": "12.34"} }
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if cart is None:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def save(self):
        self.session.modified = True

    def add(self, product, quantity=1):
        product_id = str(product.id)
        if product_id in self.cart:
            self.cart[product_id]['quantity'] += quantity
        else:
            self.cart[product_id] = {
                'quantity': quantity,
                'price': str(product.price),
            }
        self.save()

    def update(self, product_id, quantity):
        product_id = str(product_id)
        if product_id in self.cart:
            if quantity <= 0:
                self.remove(product_id)
            else:
                self.cart[product_id]['quantity'] = quantity
                self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.select_related('category').filter(id__in=product_ids)
        products_by_id = {str(p.id): p for p in products}

        for product_id, item in self.cart.items():
            product = products_by_id.get(product_id)
            if not product:
                # Product may have been deleted since being added to the cart.
                continue
            price = Decimal(item['price'])
            quantity = item['quantity']
            yield {
                'product': product,
                'quantity': quantity,
                'price': price,
                'total_price': price * quantity,
            }

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum((Decimal(item['price']) * item['quantity'] for item in self.cart.values()), Decimal('0.00'))
