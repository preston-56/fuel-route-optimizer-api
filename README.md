# Fuel Route Optimizer API

Django REST API that calculates the most cost-effective fuel stops for truck routes across the USA.

## Features

- Calculates optimal fuel stops based on cost-effectiveness
- Returns interactive HTML map with route visualization
- Handles 500-mile vehicle range with 10 MPG consumption
- Uses real fuel station data from CSV
- PostgreSQL database with spatial indexing
- Complete OpenAPI/Swagger documentation
- Fast response times (~4 seconds for cross-country routes)
- Minimal external API calls (3 total: 1 OSRM + 2 Nominatim)

## Tech Stack

- **Backend:** Django 5.0.1, Django REST Framework
- **Database:** PostgreSQL
- **External APIs:** OSRM (routing), Nominatim (geocoding)
- **Map Generation:** Folium, OpenStreetMap
- **Documentation:** drf-spectacular (OpenAPI/Swagger)

## Prerequisites

- Python 3.10+
- PostgreSQL
- pip

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/preston-56/fuel-route-optimizer-api.git
cd fuel-route-optimizer-api
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup PostgreSQL Database
```bash
# Create database and user
sudo -u postgres psql
```

In PostgreSQL shell:
```sql
CREATE DATABASE fuel_route_db;
CREATE USER fuel_route_user WITH PASSWORD 'your_secure_password';
ALTER ROLE fuel_route_user SET client_encoding TO 'utf8';
ALTER ROLE fuel_route_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE fuel_route_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE fuel_route_db TO fuel_route_user;
\c fuel_route_db
GRANT ALL ON SCHEMA public TO fuel_route_user;
\q
```

### 5. Configure Database Settings

Edit `fuel_route_api/settings.py` and update the DATABASES section:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fuel_route_db',
        'USER': 'fuel_route_user',
        'PASSWORD': 'your_secure_password',  # Change this
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 6. Run Migrations
```bash
python3 manage.py migrate
```

### 7. Load Fuel Station Data
```bash
# Use the provided CSV file
python3 manage.py load_fuel_data fuel-prices-for-be-assessment.csv

# Or load with a limit for testing
python3 manage.py load_fuel_data fuel-prices-for-be-assessment.csv --limit 200
```

### 8. Create Superuser (Optional)
```bash
python3 manage.py createsuperuser
```

### 9. Start Development Server
```bash
python3 manage.py runserver
```

API will be available at: `http://localhost:8000`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/route/` | POST | Returns JSON with optimal fuel stops and costs |
| `/api/route/map/` | POST | Returns interactive HTML map |
| `/api/health/` | GET | Health check |
| `/api/docs/` | GET | Swagger UI documentation |
| `/api/schema/` | GET | OpenAPI schema (JSON) |

## Usage Examples

### Using curl

**Get optimal route with fuel stops:**
```bash
curl -X POST http://localhost:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start":"Chicago, IL","finish":"Los Angeles, CA"}'
```

**Generate interactive map:**
```bash
curl -X POST http://localhost:8000/api/route/map/ \
  -H "Content-Type: application/json" \
  -d '{"start":"Chicago, IL","finish":"Los Angeles, CA"}' \
  -o map.html

# Open map.html in your browser
```

### Using Postman

1. **Import OpenAPI schema:** `http://localhost:8000/api/schema/`
2. **Or create manual request:**
   - Method: POST
   - URL: `http://localhost:8000/api/route/`
   - Headers: `Content-Type: application/json`
   - Body:
```json
   {
     "start": "Chicago, IL",
     "finish": "Los Angeles, CA"
   }
```

### Response Example
```json
{
  "route": {
    "distance_miles": 2017.92,
    "duration_hours": 35.5,
    "start_location": "Chicago, IL",
    "finish_location": "Los Angeles, CA"
  },
  "fuel_stops": [
    {
      "stop_number": 1,
      "station": {
        "station_id": "4437-648",
        "name": "UNDERWOOD TRUCK STOP I 80",
        "address": "I-80, EXIT 17",
        "city": "Underwood",
        "state": "IA",
        "price_per_gallon": "3.00"
      },
      "distance_from_start": 450.02,
      "fuel_amount_gallons": 50.0,
      "cost": 150.0
    }
  ],
  "total_fuel_cost": 734.68,
  "total_fuel_gallons": 221.79,
  "total_distance_miles": 2017.92,
  "response_time_ms": 4081,
  "map_endpoint": "/api/route/map/"
}
```

## Algorithm

The API uses a **greedy optimization algorithm**:

1. Start with full tank (500-mile range)
2. Travel approximately 450 miles (leaving 50-mile safety margin)
3. Query database for fuel stations within 100 miles of the route
4. Select the station with the lowest price per gallon
5. Refuel to full capacity (50 gallons)
6. Repeat until destination is reached

### Vehicle Specifications

- **Max Range:** 500 miles
- **Fuel Consumption:** 10 MPG
- **Tank Capacity:** 50 gallons

## External API Calls

Per request, the API makes:
- **1 call to OSRM** - Route calculation
- **2 calls to Nominatim** - Geocoding start and finish locations

**Total: 3 API calls per request** (all free, no API keys required)

Results are cached to minimize duplicate API calls.

## Project Structure
```
fuel-route-optimizer-api/
├── manage.py                          # Django management script
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
├── fuel-prices-for-be-assessment.csv  # Fuel station data
│
├── fuel_route_api/                    # Main project configuration
│   ├── settings.py                    # Django settings
│   ├── urls.py                        # Root URL routing
│   ├── wsgi.py                        # WSGI config
│   └── asgi.py                        # ASGI config
│
└── routing/                           # Main application
    ├── models.py                      # FuelStation database model
    ├── serializers.py                 # DRF serializers
    ├── views.py                       # API endpoints
    ├── services.py                    # Business logic
    │                                  # - RouteService (OSRM integration)
    │                                  # - FuelOptimizer (greedy algorithm)
    │                                  # - MapGenerator (Folium maps)
    ├── urls.py                        # App URL patterns
    ├── admin.py                       # Django admin configuration
    │
    ├── management/
    │   └── commands/
    │       └── load_fuel_data.py      # CSV import command
    │
    └── migrations/
        └── 0001_initial.py            # Database schema
```

## API Documentation

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/api/docs/
- **ReDoc:** http://localhost:8000/api/redoc/
- **OpenAPI Schema:** http://localhost:8000/api/schema/

## Development

### Accessing Django Admin
```bash
# Create superuser
python3 manage.py createsuperuser

# Visit http://localhost:8000/admin/
# Login with your credentials
# Manage fuel stations and view database
```

### Running Tests
```bash
python3 manage.py test
```

### Loading Custom Data

Your CSV file should have these columns:
- `OPIS Truckstop ID` or `station_id`
- `Truckstop Name` or `name`
- `Address`
- `City`
- `State`
- `Zip` or `zip_code`
- `Retail Price` or `price_per_gallon`

The `load_fuel_data` command will geocode addresses automatically.

## Performance

- **Short routes** (<500 mi): ~150-250ms
- **Medium routes** (500-1500 mi): ~250-400ms
- **Long routes** (>1500 mi): ~400-600ms

Optimizations:
- Database indexes on latitude, longitude, and price
- Route and geocoding result caching
- Single OSRM API call per request
- Efficient spatial queries using bounding boxes
- Haversine formula for distance calculations

## Requirements Met

**Django 5.0.1** - Latest stable version

**Fast API** - Response times under 5 seconds

**Minimal external API calls** - 3 calls total (1 OSRM + 2 Nominatim)

**Returns map** - Interactive HTML map with markers

**Optimal fuel stops** - Cost-effective based on prices

**500-mile range** - Implemented

**10 MPG consumption** - Implemented

**Total fuel cost** - Calculated and returned

**Uses provided CSV** - Fuel prices loaded from file

**Free APIs** - OSRM and Nominatim (no keys needed)

## Troubleshooting

### Database Connection Error
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials in settings.py
# Ensure user has proper permissions
```

### CSV Import Issues
```bash
# Check CSV format matches expected columns
# Ensure addresses are valid US locations
# Use --limit flag for testing: --limit 100
```

### Geocoding Rate Limits
The `load_fuel_data` command includes 1-second delays between geocoding requests to respect Nominatim's usage policy.

## License

MIT License

## Author

Preston Osoro

## Acknowledgments

- **OSRM** - Open Source Routing Machine
- **Nominatim** - OpenStreetMap geocoding
- **Folium** - Interactive map generation
- **Django** - Web framework