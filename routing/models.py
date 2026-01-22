from django.db import models


class FuelStation(models.Model):
    """Fuel station with location and pricing information"""
    
    station_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)
    latitude = models.FloatField()
    longitude = models.FloatField()
    price_per_gallon = models.DecimalField(max_digits=5, decimal_places=2)
    
    class Meta:
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['price_per_gallon']),
        ]
        ordering = ['price_per_gallon']
    
    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.price_per_gallon}/gal)"
