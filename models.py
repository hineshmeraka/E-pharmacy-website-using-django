# myapp/models.py
from django.db import models
from django.contrib.auth.models import User

class Products(models.Model):
    pname = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    pics = models.ImageField(upload_to='product_images/', blank=True, null=True)

    def __str__(self):
        return self.pname



class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    datetime = models.DateTimeField(auto_now_add=True)  # Automatically set on creation

    def __str__(self):
        return f'{self.product.pname} - {self.quantity}'

class Order(models.Model):
    product = models.ForeignKey(Products, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    datetime = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Processing')

    def __str__(self):
        return f'{self.product.pname} x {self.quantity} - {self.status}'
