from flask import Blueprint, render_template, url_for, make_response, request, flash
from flask_login import current_user
from flask_babelex import gettext as _
from utils.extensions import redis_client
from utils.models import User
from utils.mongo import rider_requests
from utils.helper import roles_required, resolve_redirect, logging
from bson import ObjectId
import json
from chat_bp.events import *

chat = Blueprint('chat', __name__, template_folder='chat_templates', url_prefix='/chat')

@chat.before_request
@roles_required(['driver', 'rider'])
def ensure_routes_protected():
    """ make sure user is a driver or rider before accessing any chat route """
    pass

@chat.after_request
def no_cache(response):
    """ add no cache headers to all chat routes """
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# split over two routes for clear distinct roles_required
@chat.get('/driver/<ride_request_id>')
@roles_required(['driver'])
def driver(ride_request_id):

    """ view chat as driver with rider """

    try:
        # get the ride request id 
        ride_request_id = ObjectId(ride_request_id)
        # get the active ride request
        active_ride = rider_requests.find_one({'driver_id': current_user.id, 'status': 'accepted', '_id': ride_request_id})
        if not active_ride:
            raise ValueError('No active ride found')
        
        # get the rider id from the active ride request
        recipient_id = active_ride.get('rider_id')
        recipient = User.get_by_id(recipient_id)
        recipient.ride_role = _('Rider')

        # TODO add fetch more messages on scroll
        # get the last 50 messages from redis
        messages = redis_client.zrevrange(f'messages:{ride_request_id}', 0, 50)
        messages = [json.loads(message) for message in messages]
        messages.reverse()

        resp = make_response(render_template('chat_index.html', recipient=recipient, room=ride_request_id, messages=messages))
        if 'hx-request' in request.headers:
            resp.headers['HX-Trigger-After-Swap'] = json.dumps({'initChat': {'room': str(ride_request_id), 'user_id':current_user.id, 'recipient_id': recipient_id, }})
        
        return resp
    
    except ValueError as ve:
        logging.error(f"ERROR @ {request.endpoint}: {ve}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        flash(_('No active ride found'), 'error')
        return resolve_redirect(url_for('inter.drivers.index'))
    
    except TypeError as te:
        logging.error(f"ERROR @ {request.endpoint}: {te}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        flash(_('Sorry we could not process this request'), 'error')
        return resolve_redirect(url_for('inter.drivers.index'))
        
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        flash(_('Server Error'), 'error')
        return resolve_redirect(url_for('inter.drivers.index'))
    

@chat.get('/rider/<ride_request_id>')
@roles_required(['rider'])
def rider(ride_request_id):

    """ view chat as rider with driver """

    try:

        # get the ride request id from the query string
        ride_request_id = ObjectId(ride_request_id)
        # get the active ride request
        active_ride = rider_requests.find_one({'rider_id': current_user.id, 'status': 'accepted', '_id': ride_request_id})
        if not active_ride:
            raise ValueError('No active ride found')
        
        # get the driver id from the active ride request
        recipient_id = active_ride.get('driver_id')
        recipient = User.get_by_id(recipient_id)
        recipient.ride_role = ('Driver')
        
        # get the last 50 messages from redis
        messages = redis_client.zrevrange(f'messages:{ride_request_id}', 0, 50)
        messages = [json.loads(message) for message in messages]
        messages.reverse()

        return render_template('chat_index.html', recipient=recipient, room=ride_request_id, messages=messages)
        
    except ValueError as ve:
        logging.error(f"ERROR @ {request.endpoint}: {ve}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        flash(_('No active ride found'), 'error')
        return resolve_redirect(url_for('inter.riders.index'))
    
    except TypeError as te:
        logging.error(f"ERROR @ {request.endpoint}: {te}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        flash(_('Sorry we could not process this request'), 'error')
        return resolve_redirect(url_for('inter.riders.index'))
        
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        flash(_('Server Error'), 'error')
        return resolve_redirect(url_for('inter.riders.index'))
    



