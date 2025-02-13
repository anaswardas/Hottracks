from django.db import models
from django.utils import timezone
from accounts.models import Users, Address
from product.models import Product
from decimal import Decimal
from django.conf import settings
import uuid




class Cart(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Cart of {self.user.username} - {'Active' if self.is_active else 'Inactive'}"

    def subtotal(self):
        return sum(item.subtotal() for item in self.items.all())

    def calculate_tax(self, tax_rate=Decimal('0.001')):
        return self.subtotal() * tax_rate




class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def subtotal(self):
        return Decimal(self.product.price) * Decimal(self.quantity)



  
class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment = models.OneToOneField('payment.Payment', on_delete=models.CASCADE, related_name='order')
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    orderid = models.CharField(max_length=100, unique=True, blank=True, null=True)

    coupon = models.ForeignKey('payment.Coupon', on_delete=models.SET_NULL, null=True, blank=True)  

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),  
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    SHIPPING_STATUSES = [
        ('Pending', 'Pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),  
    ]
    shipping_status = models.CharField(max_length=20, choices=SHIPPING_STATUSES, default='Pending')

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.orderid:
            self.orderid = str(uuid.uuid4())[:8]

        if self.shipping_status == "Delivered":
            self.status = "Delivered"
        elif self.shipping_status == "Cancelled":
            self.status = "Cancelled"
        elif self.shipping_status == "Shipped":
            self.status = "Shipped"
        elif self.shipping_status == "Returned":  
            self.status = "Returned"
        else:
            self.status = "Pending"

        super(Order, self).save(*args, **kwargs)


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)

    def __str__(self) -> str:
        return f"{self.product} on {self.added_on}"

    @property
    def wishlist_sub_count(self):
        wishlist_items = self.product.all()
        total = wishlist_items.count()
        return total
