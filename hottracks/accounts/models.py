from django.contrib.auth.models import AbstractUser
from django.db import models


class Users(AbstractUser):
    phone_number = models.IntegerField(null=True, blank=True)  
    profile_image = models.ImageField(upload_to='profile_pics/', default='default.jpg', blank=True)  

    groups = models.ManyToManyField(
        'auth.Group', 
        related_name='custom_user_set',  
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True
    )

    def __str__(self):
        return self.username


class Address(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='addresses')  
    name = models.CharField(max_length=100, blank=True, null=True)  
    email = models.EmailField(max_length=150)  
    phone = models.CharField(max_length=15)  
    house_no = models.CharField(max_length=100, blank=True, null=True)  
    city = models.CharField(max_length=50)  
    state = models.CharField(max_length=50)  
    country = models.CharField(max_length=50)  
    pincode = models.CharField(max_length=20)  
    is_delete = models.BooleanField(default=False, null=True)  

    def __str__(self):
        return f"{self.name}, {self.city}, {self.state}, {self.country}"

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        
        

 