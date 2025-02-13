from django.db import models
from django.conf import settings
from product.models import Product
from cart.models import Order
from django.db import models
from django.conf import settings
from django.utils import timezone
import razorpay
from decimal import Decimal
from django.utils.timezone import now

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]
    
    PAYMENT_METHODS = [
        ('RAZORPAY', 'Razorpay'),
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_gateway = models.CharField(max_length=100, default='RAZORPAY')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='RAZORPAY')
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.status}"

    def create_razorpay_order(self):
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order_data = {
            'amount': int(self.amount * 100), 
            'currency': 'INR',
            'payment_capture': 1
        }
        razorpay_order = client.order.create(data=order_data)
        self.razorpay_order_id = razorpay_order['id']
        self.save()
        return razorpay_order

    def verify_razorpay_payment(self, razorpay_payment_id, razorpay_signature):
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': self.razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            
            payment_details = client.payment.fetch(razorpay_payment_id)
            
            if payment_details['status'] == 'captured':
                self.status = 'Completed'
                self.razorpay_payment_id = razorpay_payment_id
                self.razorpay_signature = razorpay_signature
                self.save()
                return True
            else:
                self.status = 'Failed'
                self.save()
                return False
        
        except Exception as e:
            self.status = 'Failed'
            self.save()
            return False


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} - Order #{self.order.id}"
    
    def subtotal(self):
        return self.price * self.quantity
 
 


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance}"

    def add_amount(self, amount):
        if amount > 0:
            self.balance += amount
            self.save()
        else:
            raise ValueError("Amount to be added must be positive.")

    def deduct_amount(self, amount):
      
        if self.balance >= amount:
            self.balance -= amount
            self.save()
        else:
            raise ValueError("Insufficient balance to deduct this amount.")

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('CANCELLED_ORDER', 'Cancelled Order Refund'),
        ('RETURNED_ORDER', 'Returned Order Refund'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"




class Coupon(models.Model):
    title = models.CharField(max_length=255)  
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    start_date = models.DateTimeField(default=now)  
    end_date = models.DateTimeField(null=True, blank=True) 
    quantity = models.PositiveIntegerField(default=1)  
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    def is_valid(self, user):
        if not self.is_active or (self.end_date and self.end_date < now()):
            return False  
        return not CouponUsage.objects.filter(user=user, coupon=self).exists()

    def apply_discount(self, total_amount, user):
        if self.is_valid(user):
            discount_amount = total_amount * (self.discount_percentage / 100)
            return max(0, total_amount - discount_amount)
        return total_amount  

    def __str__(self):
        return f"{self.code} - {self.discount_percentage}%"




class CouponUsage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_usage")
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="coupon_usage")
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} used {self.coupon.code} on {self.used_at.strftime('%Y-%m-%d %H:%M:%S')}"
