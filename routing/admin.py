from django.contrib import admin
from .models import FuelStation


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'price_per_gallon', 'latitude', 'longitude']
    list_filter = ['state', 'city']
    search_fields = ['name', 'city', 'state', 'address']
    ordering = ['price_per_gallon']
    list_per_page = 50
    
    fieldsets = (
        ('Station Information', {
            'fields': ('station_id', 'name', 'address', 'city', 'state', 'zip_code')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Pricing', {
            'fields': ('price_per_gallon',)
        }),
    )
