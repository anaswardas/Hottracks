from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    category_image = models.ImageField(upload_to='category_images/', blank=True, null=True)  
    def __str__(self):
        return self.name

    def unlist(self):
        self.is_active = False
        self.save()
        self.products.update(is_in_stock=False)

    def list(self):
        self.is_active = True
        self.save()



class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_in_stock = models.BooleanField(default=True)
    stock_count = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    is_offer_applied = models.BooleanField(default=False)  
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  
    validate_offerdate = models.DateField(blank=True, null=True)  
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  

    def __str__(self):
        return self.name

    def clean(self):
        images = [self.image1, self.image2, self.image3]
        if not any(images):
            raise ValidationError("At least 3 images must be uploaded.")

    def save(self, *args, **kwargs):
        if not self.category.is_active:
            self.is_in_stock = False
        super().save(*args, **kwargs)





class Offer(models.Model):
    OFFER_TYPES = [
        ('product', 'Product Offer'),
        ('category', 'Category Offer'),
    ]

    name = models.CharField(max_length=255, unique=True)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPES)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Discount percentage (e.g., 10 for 10%)"
    )
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    applicable_product = models.ManyToManyField(
        'Product', blank=True, related_name='product_offers'
    ) 
    applicable_category = models.ManyToManyField(
        'Category', blank=True, related_name='category_offers'
    ) 

    def clean(self):
        if self.offer_type == 'product' and not self.applicable_product.exists():
            raise ValidationError("Product offer must be linked to at least one product.")
        if self.offer_type == 'category' and not self.applicable_category.exists():
            raise ValidationError("Category offer must be linked to at least one category.")
        if self.discount_percentage <= 0 or self.discount_percentage > 100:
            raise ValidationError("Discount percentage must be between 1 and 100.")

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

    def apply_discount(self, original_price):
        discount_amount = (original_price * (self.discount_percentage / Decimal("100")))
        new_price = max(original_price - discount_amount, Decimal("0"))
        return new_price.quantize(Decimal("0.01"))  

    def __str__(self):
        return f"{self.name} ({self.get_offer_type_display()} - {self.discount_percentage}%)"
