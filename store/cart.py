from decimal import Decimal

CART_SESSION_KEY = 'adtech_cart'


class Cart:
    """Session-based shopping cart."""

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if not cart:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.selling_price),
                'name': product.name,
            }
        if update_quantity:
            self.cart[product_id]['quantity'] = int(quantity)
        else:
            self.cart[product_id]['quantity'] += int(quantity)

        # Clamp to available stock
        if self.cart[product_id]['quantity'] > product.stock_quantity:
            self.cart[product_id]['quantity'] = product.stock_quantity

        # Remove if zero
        if self.cart[product_id]['quantity'] <= 0:
            del self.cart[product_id]

        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        if CART_SESSION_KEY in self.session:
            del self.session[CART_SESSION_KEY]
        self.save()

    def save(self):
        self.session.modified = True

    def get_total_price(self):
        return sum(
            Decimal(item['price']) * item['quantity']
            for item in self.cart.values()
        )

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def __iter__(self):
        from inventory.models import Product
        product_ids = self.cart.keys()
        products = {str(p.id): p for p in Product.objects.filter(id__in=product_ids)}
        for pid, item in self.cart.items():
            product = products.get(pid)
            if product:
                yield {
                    'product': product,
                    'quantity': item['quantity'],
                    'price': Decimal(item['price']),
                    'total_price': Decimal(item['price']) * item['quantity'],
                }

    def is_empty(self):
        return len(self.cart) == 0
