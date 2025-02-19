# models.py
from django.db import models

class Product(models.Model):
    title = models.CharField(max_length=255)
    price = models.FloatField()
    category = models.CharField(max_length=100)
    image_url = models.URLField()
