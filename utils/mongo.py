from pymongo.mongo_client import MongoClient
from gridfs import GridFS
from utils.config import MONGO_URL

# Mongo DB 
client = MongoClient(MONGO_URL)
mongo_db = client['KUber']

# model for ride options: {name, id, ride_type, image, base_fare, frare_rate, time_rate, capacity}
ride_options = mongo_db['ride_options']

# model for payment methods: {user_id, method, date, is_starred} *if is paypal, { email }, if is card, { card_number, expiry_date, cvv, country }}, if is cash, { }
payment_methods = mongo_db['payment_methods']

# model for driver data: {user_id, status, date_added, license_number, license_expirey_date, vehicle_plate, ride_option, license_photo, vehicle_phot}
driver_data = mongo_db['driver_data']
gridfs = GridFS(mongo_db)

# model for rider requests { rider_id, created_at, pickup_lat, pickup_lon, pickup_osm_id, dropoff_lat, dropoff_lon, dropoff_osm_id, ride_option, status} * when status is accepted, driver_id, distance, ended_at are added
# status: pending, accepted, completed, cancelled
rider_requests = mongo_db['rider_requests']

# opt for cached routes in mongo db due to extremely limited redis memory
#model for cached routes
cached_routes = mongo_db['cached_routes']

# model for cached geocodes
cached_geocodes = mongo_db['cached_geocodes']
