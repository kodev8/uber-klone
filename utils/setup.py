import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mongo import ride_options, payment_methods, cached_geocodes, cached_routes, driver_data, rider_requests, mongo_db
from utils.extensions import redis_client, db
from utils.models import User, UserRoles
from utils.helper import logging
from flask import Flask
from utils.config import Config
app = Flask(__name__)
app.config.from_object(Config)
redis_client.init_app(app)
db.init_app(app)

def setup_app():
    """ set up app """
    try:    
        print('Setting up app...')

        # set up ride options
        with open("setup.json", "r") as read_file:
            set_up_json = json.load(read_file)
            # clear ride options
            ride_options.delete_many({})
            ride_options.insert_many(set_up_json['ride_options'])
            print('Ride Options Set Up Successully')

        
        # payment_methods.delete_many({})
        print('Payment Methods Flushed Successfully')

        cached_geocodes.delete_many({})
        cached_routes.delete_many({})
        print('GeoCache amd Routes Flushed Successfully')

        driver_data.delete_many({})
        mongo_db['fs.files'].delete_many({})
        mongo_db['fs.chunks'].delete_many({})
        print('Driver Data Flushed Successfully')

        rider_requests.delete_many({})
        print('Rider Requests Flushed Successfully')

        redis_client.flushall()
        print('Redis Flushed Successfully')

        # create admin user
        with app.app_context():
            User.remove_all()
            UserRoles.remove_all()
            User.create_admin()
            print('Removed users and created admin')
        
    except Exception as e:
        logging.error(f"ERROR in setup {e}", exc_info=True, stack_info=True, stacklevel=2)
        print('Error in setup: ', e)

if __name__ == "__main__":
    setup_app()
