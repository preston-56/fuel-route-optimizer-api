import csv
import time
import requests
from django.core.management.base import BaseCommand
from routing.models import FuelStation


class Command(BaseCommand):
    help = 'Load fuel station data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--limit', type=int, default=None, help='Max stations to load')

    def geocode_city_state(self, city, state):
        """Geocode using just city and state (more reliable)"""
        location = f"{city}, {state}, USA"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'us'
        }
        headers = {'User-Agent': 'FuelRouteOptimizer/1.0'}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
        except:
            pass
        return None, None

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        limit = options.get('limit')

        self.stdout.write(f'Loading fuel data from {csv_file}...')

        FuelStation.objects.all().delete()

        count = 0
        skipped = 0
        geocode_cache = {}
        row_num = 0

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)

            for row in reader:
                row_num += 1

                if limit and count >= limit:
                    break

                try:
                    station_id_base = row['OPIS Truckstop ID'].strip()
                    name = row['Truckstop Name'].strip()
                    address = row['Address'].strip()
                    city = row['City'].strip()
                    state = row['State'].strip()
                    price_str = row['Retail Price'].strip()

                    if not all([station_id_base, name, city, state, price_str]):
                        skipped += 1
                        continue

                    station_id = f"{station_id_base}-{row_num}"

                    try:
                        price = float(price_str)
                    except:
                        skipped += 1
                        continue

                    cache_key = f"{city},{state}"

                    if cache_key in geocode_cache:
                        lat, lon = geocode_cache[cache_key]
                    else:
                        self.stdout.write(f'Geocoding: {city}, {state}')
                        lat, lon = self.geocode_city_state(city, state)
                        geocode_cache[cache_key] = (lat, lon)
                        time.sleep(1)

                    if lat is None:
                        self.stdout.write(self.style.WARNING(f'Could not geocode: {city}, {state}'))
                        skipped += 1
                        continue

                    FuelStation.objects.create(
                        station_id=station_id,
                        name=name,
                        address=address or 'N/A',
                        city=city,
                        state=state,
                        zip_code='00000',
                        latitude=lat,
                        longitude=lon,
                        price_per_gallon=price
                    )
                    count += 1

                    if count % 50 == 0:
                        self.stdout.write(self.style.SUCCESS(f'Loaded {count} stations...'))

                except KeyError as e:
                    self.stdout.write(self.style.ERROR(f'Missing column: {e}'))
                    return
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error on row {row_num}: {e}'))
                    skipped += 1

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully loaded {count} fuel stations')
        )
        if skipped > 0:
            self.stdout.write(
                self.style.WARNING(f'Skipped {skipped} stations')
            )
