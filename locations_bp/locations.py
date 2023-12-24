from flask import Blueprint, request, render_template, jsonify
from flask_babelex import gettext as _
from utils.helper import roles_required, logging
from utils.codes import CODES
from utils.helper import htmx_request
from utils.config import LOCATIONS_API_URL, LOCATIONS_API_KEY, FLASK_TESTING
from utils.notifications import notify_accept_error_modal
from utils.mongo import cached_routes, cached_geocodes
import locations_bp.sample as sample
from geopy.distance import distance
import requests

cache = {}

locations = Blueprint('locations', __name__, template_folder='locations_templates', url_prefix='/locations')

@locations.get("/search")
@roles_required(['rider'])
@htmx_request
def search_locations():

    q = request.args.get('pickup') or request.args.get('dropoff')

    # check if query is valid , use min search to avoid most likely useless call to api
    if not q or len(q) < 3:
        return ''
    
    search_type = 'pickup' if 'pickup' in request.args else 'dropoff'

    if q in cache:
        return render_template('locations_htmx/search-results.html', data=cache[q], search_type=search_type)
    
    params = {
        "key": LOCATIONS_API_KEY,
        "q":   q,
        "limit": 10,
    }

    try:
        if FLASK_TESTING:
            data = sample.data

        else:
            r = requests.get(f'{LOCATIONS_API_URL}/autocomplete', params=params)
            if r.status_code != 200:
                logging.error(f"ERROR @ {request.endpoint}: LocationIQ Bad Api Search", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request, 'api_response':r})
                # print('Failed at api search location request', r.status_code, r.url)
                raise Exception('Failed at api search location request')
            
            data = r.json()
            cache[q] = data
    
        return render_template('locations_htmx/search-results.html', data=data, search_type=search_type)
        
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        return notify_accept_error_modal(_('We are currently unable to process you request. Please try again later'), header=_("Server Error"), code=CODES.INTERNAL_SERVER_ERROR)
    

# lat lon dicts
def find_route(origin_lat, origin_lon, origin_osm_id, destination_lat, destination_lon, destination_osm_id):

    """ Checks if a route is possible between two locations"""
    # print(origin_lat, origin_lon, origin_osm_id, destination_lat, destination_lon, destination_osm_id)
    try:

        # chekc if origin is destination
        if (origin_lat == destination_lat and origin_lon == destination_lon ) or (origin_osm_id == destination_osm_id):
            raise ValueError('Origin cannot be destinatin')

        distance_between = distance((origin_lat, origin_lon), (destination_lat, destination_lon)).km
        # print(distance_between)
        # api is limited to 10,000 km
        if distance_between > 10000 or distance_between < 0.2:
            raise ValueError(f'Route cannot be found {distance_between}')

        route = cached_routes.find_one({
            'origin': origin_osm_id,
            'destination': destination_osm_id,
        })

        if route:
            # print('Found in cache, routing...')
            return route
        
        # format as lon lat for location iq specifications
        origin = f"{origin_lon},{origin_lat}"
        destination = f"{destination_lon},{destination_lat}"
        params = {
            "key": LOCATIONS_API_KEY,
            "steps": "true",
            "alternatives": "false",
            "geometries": "polyline",
            "overview": "full",
        
        }
        url = f"{LOCATIONS_API_URL}/directions/driving/{origin};{destination}"
        directions_result = requests.get(url, params=params)

        # Check if there is at least one route
        if not directions_result:
            raise ValueError('Route cannot be found')
        
        # print("Route is possible!")
        # directions_result.json()) 

        res = directions_result.json()
        cached_routes.insert_one({
            'origin':origin_osm_id,
            'destination': destination_osm_id,
        } | res)

        return res
    except Exception as e:
        logging.error(f"ERROR @ find_route: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'origin':(origin_lat, origin_lon, origin_osm_id), 'destination': (destination_lat, destination_lon, destination_osm_id)})
        # print("Error while checking route.", e)
        return False

def calculate_fare(distance, duration, car_type, formatted=True):
    """ Calculates the fare of a ride based on distance and duration 
        params: distance in m, duration in seconds, car_type: dict from mongodb car options
    """

    # convert seconds to minutes
    duration /= 60
    distance /= 1000
    

    time_charge = duration * car_type['time_rate']
    distance_charge = distance * car_type['fare_rate']
    total_fare = car_type['base_fare'] + distance_charge + time_charge
    
    total_fare = round(total_fare, 2)
    
    if formatted:
        return  f"{total_fare:.2f}"
    else:
        return total_fare

def reverse_geocode(lat, lon, osm_id):
    """ Reverse geocode a location using location iq api """
    try:

        # check if location is in cache
        geocode = cached_geocodes.find_one({'$or': [
                {'lat': lat, 'lon': lon},
                {'osm_id': osm_id}
            ]
        })

        if geocode:
            del geocode['_id']
            return geocode
    
        params = {
            "key": LOCATIONS_API_KEY,
            "lat": lat,
            "lon": lon,
            "format": "json"
        }

        # res = {}
        r = requests.get(f"{LOCATIONS_API_URL}/reverse", params=params)
        if r.status_code != 200:
            raise Exception('Failed to reverse geocode')
        
        res = r.json()

        # cache result as copy since it is changed in place by mongo
        cached_geocodes.insert_one(res.copy())

        return res
    
    except Exception as e:
        logging.error(f"ERROR @ reverse_geocode: {e}", exc_info=True, stack_info=True, stacklevel=3, extra={'lat':lat, 'lon':lon, 'osm_id':osm_id})
        return jsonify({'error':'Missing info'}), CODES.BAD_REQUEST
    
@locations.route('/reverse-geocode')
@htmx_request
def reverse_geocode_route():
    """ Reverse geocode a location using location iq api """
    try:
        lat = request.args.get('lat')
        lon = request.args.get('lon')

        if not all([lat, lon]):
            raise ValueError('Missing info')
        
        return reverse_geocode(lat, lon, None)
    
    except Exception as e:
        # may  not be called
        logging.error(f"ERROR @ reverse_geocode_route: {e}", exc_info=True, stack_info=True, stacklevel=3, extra={'lat':lat, 'lon':lon})
        return jsonify({'error':'Missing info'}), CODES.BAD_REQUEST

# JSON RESPONSE OF ROUTE DATA AS IT IS TOO LARGE TO SEND IN HEADER/COOKIES OR AS A URL PARAM
@locations.route('/route-data')
@htmx_request
def route_data():

    """ Get route data from cache or api as json"""

    try:
    
        pickup_lat = request.args.get('pickup_lat')
        pickup_lon = request.args.get('pickup_lon')
        pickup_osm_id = request.args.get('pickup_osm_id')

        dropoff_lat = request.args.get('dropoff_lat')
        dropoff_lon = request.args.get('dropoff_lon')
        dropoff_osm_id = request.args.get('dropoff_osm_id')


        if not all([pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, pickup_osm_id, dropoff_osm_id]):
            print('fail1')
            return jsonify({'error':'Missing info'}), CODES.BAD_REQUEST

        route = find_route(pickup_lat, pickup_lon, pickup_osm_id, dropoff_lat, dropoff_lon, dropoff_osm_id)
        if not route:
            raise Exception('Route not found')
        
        return route['routes'][0]
    
    except Exception as e:
        logging.error(f"ERROR @ route_data: {e}", exc_info=True, stack_info=True, stacklevel=3, extra={'pickup':(pickup_lat, pickup_lon, pickup_osm_id), 'dropoff': (dropoff_lat, dropoff_lon, dropoff_osm_id)})
        return jsonify({'error':'Missing info'}), CODES.BAD_REQUEST



# def get_user_ip():
#     r = requests.get("http://ipinfo.io/json")
#     print(r.json() )

    # response = client.get_price_estimates(
    # start_latitude=37.770,
    # start_longitude=-122.411,
    # end_latitude=37.791,
    # end_longitude=-122.405,
    # seat_count=2
    #     )

    # estimate = response.json.get('prices')
    # r.json()
    # return jsonify({
    #     'req_rom_addr':request.remote_addr,
    #     'req_env_rom_addr':request.environ['REMOTE_ADDR'],
    #     # 'estmate':estimate

                    # } | r.json())
    # search = request.args.get('search')
    # if not search:
    #     return [], CODES.NO_CONTENT
    
    # # send search to location api
    # try:
    #     r = requests.get(LOCATION_API_URL + "/search", params={'search': search})
    #     resp = r.json()
    #     if str(r.status_code)[0] != '2':
    #         return render_template('htmx/search_error.html',)
        
    #     else:
    #         return resp, CODES.BAD_REQUEST
        
    # except Exception as e:
    #     print(e)
    #     return [], CODES.INTERNAL_SERVER_ERROR
