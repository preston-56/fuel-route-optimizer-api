from rest_framework import serializers
from .models import FuelStation


class FuelStationSerializer(serializers.ModelSerializer):
    """Serializer for FuelStation model"""
    
    class Meta:
        model = FuelStation
        fields = ['station_id', 'name', 'address', 'city', 'state', 
                  'zip_code', 'latitude', 'longitude', 'price_per_gallon']


class RouteRequestSerializer(serializers.Serializer):
    """Validate route request input"""
    start = serializers.CharField(max_length=200)
    finish = serializers.CharField(max_length=200)


class FuelStopSerializer(serializers.Serializer):
    """Individual fuel stop information"""
    stop_number = serializers.IntegerField()
    station = FuelStationSerializer()
    distance_from_start = serializers.FloatField()
    cumulative_distance = serializers.FloatField()
    fuel_amount_gallons = serializers.FloatField()
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)


class RouteResponseSerializer(serializers.Serializer):
    """Complete route response"""
    route = serializers.DictField()
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_fuel_gallons = serializers.FloatField()
    total_distance_miles = serializers.FloatField()
    response_time_ms = serializers.IntegerField()
    map_url = serializers.URLField(required=False, allow_null=True)
