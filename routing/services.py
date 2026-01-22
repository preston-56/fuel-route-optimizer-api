import requests
import math
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from django.core.cache import cache
from .models import FuelStation


class RouteService:
    """Handles external routing API calls"""

    def get_route(self, start: str, finish: str) -> Dict:
        cache_key = f"route:{start}:{finish}".replace(" ", "_").replace(",", "")
        cached_route = cache.get(cache_key)
        if cached_route:
            return cached_route

        start_coords = self._geocode(start)
        finish_coords = self._geocode(finish)
        route_data = self._get_route_osrm(start_coords, finish_coords)

        cache.set(cache_key, route_data, 3600)
        return route_data

    def _geocode(self, location: str) -> Tuple[float, float]:
        cache_key = f"geocode:{location}".replace(" ", "_").replace(",", "")
        cached_coords = cache.get(cache_key)
        if cached_coords:
            return cached_coords

        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'us'
        }
        headers = {'User-Agent': 'FuelRouteOptimizer/1.0'}

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise ValueError(f"Could not find location: {location}")

        coords = (float(data[0]['lon']), float(data[0]['lat']))
        cache.set(cache_key, coords, 86400)
        return coords

    def _get_route_osrm(self, start: Tuple[float, float], finish: Tuple[float, float]) -> Dict:
        url = f"http://router.project-osrm.org/route/v1/driving/{start[0]},{start[1]};{finish[0]},{finish[1]}"
        params = {'overview': 'full', 'geometries': 'geojson', 'steps': 'true'}

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data['code'] != 'Ok':
            raise ValueError("Routing failed")

        route = data['routes'][0]
        distance_meters = route['distance']
        duration_seconds = route['duration']
        geometry = route['geometry']['coordinates']
        waypoints = self._extract_waypoints(geometry, distance_meters)

        return {
            'distance_miles': distance_meters * 0.000621371,
            'duration_hours': duration_seconds / 3600,
            'geometry': geometry,
            'waypoints': waypoints,
            'start_coords': start,
            'finish_coords': finish
        }

    def _extract_waypoints(self, geometry: List, total_distance_meters: float) -> List[Tuple]:
        waypoints = []
        interval_miles = 50
        interval_meters = interval_miles * 1609.34
        cumulative_distance = 0
        waypoints.append((geometry[0][0], geometry[0][1], 0))

        for i in range(1, len(geometry)):
            prev_point = geometry[i-1]
            curr_point = geometry[i]
            segment_distance = self._haversine_distance(
                prev_point[1], prev_point[0], curr_point[1], curr_point[0]
            )
            cumulative_distance += segment_distance

            if cumulative_distance >= interval_meters * (len(waypoints)):
                waypoints.append((
                    curr_point[0], curr_point[1],
                    cumulative_distance * 0.000621371
                ))

        if waypoints[-1][2] < total_distance_meters * 0.000621371 - 10:
            waypoints.append((
                geometry[-1][0], geometry[-1][1],
                total_distance_meters * 0.000621371
            ))

        return waypoints

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi/2)**2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c


class FuelOptimizer:
    """Optimizes fuel stops using greedy algorithm"""

    MAX_RANGE_MILES = 500
    MPG = 10
    TANK_CAPACITY_GALLONS = MAX_RANGE_MILES / MPG
    SEARCH_RADIUS_MILES = 100
    SAFETY_MARGIN_MILES = 50

    def __init__(self, route_data: Dict):
        self.route_data = route_data
        self.total_distance = route_data['distance_miles']
        self.waypoints = route_data['waypoints']

    def calculate_optimal_stops(self) -> List[Dict]:
        stops = []
        current_distance = 0
        fuel_range_remaining = self.MAX_RANGE_MILES
        stop_number = 1

        while current_distance + fuel_range_remaining < self.total_distance:
            next_stop_distance = min(
                current_distance + self.MAX_RANGE_MILES - self.SAFETY_MARGIN_MILES,
                self.total_distance
            )

            station = self._find_cheapest_station_near_distance(
                next_stop_distance, self.SEARCH_RADIUS_MILES
            )

            if not station:
                for expanded_radius in [150, 200, 250]:
                    station = self._find_cheapest_station_near_distance(
                        next_stop_distance, expanded_radius
                    )
                    if station:
                        break

            if not station:
                next_stop_distance = current_distance + (fuel_range_remaining / 2)
                station = self._find_cheapest_station_near_distance(
                    next_stop_distance, self.SEARCH_RADIUS_MILES * 2
                )

            if not station:
                raise ValueError(
                    f"No fuel station found near mile {next_stop_distance:.1f}. "
                    f"Try loading more fuel stations or testing a different route."
                )

            station_distance = self._get_station_distance_on_route(station)
            fuel_to_buy = self.TANK_CAPACITY_GALLONS

            stop_info = {
                'stop_number': stop_number,
                'station': station,
                'distance_from_start': station_distance,
                'cumulative_distance': station_distance,
                'fuel_amount_gallons': float(fuel_to_buy),
                'cost': Decimal(str(fuel_to_buy)) * station.price_per_gallon
            }

            stops.append(stop_info)
            current_distance = station_distance
            fuel_range_remaining = self.MAX_RANGE_MILES
            stop_number += 1

        return stops

    def _find_cheapest_station_near_distance(self, target_distance: float,
                                             radius: float) -> Optional[FuelStation]:
        closest_waypoint = min(self.waypoints, key=lambda wp: abs(wp[2] - target_distance))
        waypoint_lon, waypoint_lat, waypoint_dist = closest_waypoint

        nearby_stations = self._find_stations_in_radius(waypoint_lat, waypoint_lon, radius)

        if not nearby_stations:
            return None

        return min(nearby_stations, key=lambda s: s.price_per_gallon)

    def _find_stations_in_radius(self, lat: float, lon: float,
                                 radius_miles: float) -> List[FuelStation]:
        lat_degree_miles = 69.0
        lon_degree_miles = 69.0 * math.cos(math.radians(lat))
        lat_delta = radius_miles / lat_degree_miles
        lon_delta = radius_miles / lon_degree_miles

        stations = FuelStation.objects.filter(
            latitude__gte=lat - lat_delta,
            latitude__lte=lat + lat_delta,
            longitude__gte=lon - lon_delta,
            longitude__lte=lon + lon_delta
        )

        nearby = []
        for station in stations:
            distance = self._calculate_distance(lat, lon, station.latitude, station.longitude)
            if distance <= radius_miles:
                nearby.append(station)

        return nearby

    def _get_station_distance_on_route(self, station: FuelStation) -> float:
        closest_waypoint = min(
            self.waypoints,
            key=lambda wp: self._calculate_distance(
                station.latitude, station.longitude, wp[1], wp[0]
            )
        )
        return closest_waypoint[2]

    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 3959
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi/2)**2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c


class MapGenerator:
    """Generates map visualization"""

    @staticmethod
    def generate_map_html(route_data: Dict, fuel_stops: List[Dict]) -> str:
        """Generate interactive HTML map with route and fuel stops"""
        try:
            import folium
        except ImportError:
            return "<p>Map generation requires folium library. Install with: pip install folium</p>"

        start = route_data['start_coords']
        finish = route_data['finish_coords']
        center_lat = (start[1] + finish[1]) / 2
        center_lon = (start[0] + finish[0]) / 2

        distance = route_data['distance_miles']
        zoom = 5 if distance > 1000 else (6 if distance > 500 else 7)

        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

        # Start marker (green)
        folium.Marker(
            [start[1], start[0]],
            popup=f"<b>Start:</b> {route_data.get('start_location', 'Start')}",
            icon=folium.Icon(color='green', icon='play')
        ).add_to(m)

        # Finish marker (red)
        folium.Marker(
            [finish[1], finish[0]],
            popup=f"<b>Finish:</b> {route_data.get('finish_location', 'Finish')}",
            icon=folium.Icon(color='red', icon='stop')
        ).add_to(m)

        # Route line (blue)
        route_coords = [[coord[1], coord[0]] for coord in route_data['geometry']]
        folium.PolyLine(
            route_coords,
            color='blue',
            weight=4,
            opacity=0.7,
            popup=f"Route: {distance:.1f} miles"
        ).add_to(m)

        # Fuel stops (orange markers)
        for stop in fuel_stops:
            station = stop['station']
            # Handle both dict and object
            if isinstance(station, dict):
                lat = station['latitude']
                lon = station['longitude']
                name = station['name']
                city = station['city']
                state = station['state']
                price = station['price_per_gallon']
            else:
                lat = station.latitude
                lon = station.longitude
                name = station.name
                city = station.city
                state = station.state
                price = station.price_per_gallon

            folium.Marker(
                [lat, lon],
                popup=f"""
                <div style='width: 200px'>
                    <b>Stop #{stop['stop_number']}</b><br>
                    <b>{name}</b><br>
                    {city}, {state}<br>
                    <hr>
                    <b>Price:</b> ${price}/gal<br>
                    <b>Distance:</b> {stop['distance_from_start']:.1f} mi<br>
                    <b>Fuel:</b> {stop['fuel_amount_gallons']:.1f} gal<br>
                    <b>Cost:</b> ${float(stop['cost']):.2f}
                </div>
                """,
                icon=folium.Icon(color='orange', icon='info-sign')
            ).add_to(m)

        return m._repr_html_()

    @staticmethod
    def generate_map_url(route_data: Dict, fuel_stops: List[Dict]) -> str:
        """Generate OpenStreetMap URL"""
        start = route_data['start_coords']
        finish = route_data['finish_coords']
        center_lat = (start[1] + finish[1]) / 2
        center_lon = (start[0] + finish[0]) / 2

        distance = route_data['distance_miles']
        zoom = 5 if distance > 1000 else (6 if distance > 500 else 7)

        return f"https://www.openstreetmap.org/?mlat={center_lat}&mlon={center_lon}#map={zoom}/{center_lat}/{center_lon}"