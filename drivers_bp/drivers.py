from flask import Blueprint, render_template, url_for, make_response, flash
from flask_login import current_user
from flask_babelex import gettext as _
from utils.helper import roles_required, resolve_redirect
from utils.mongo import rider_requests, driver_data, ride_options
from utils.models import User
from utils.helper import htmx_request
from utils.notifications import notify_accept_error_modal
from utils.codes import CODES
from utils.extensions import socketio
from wtforms.validators import ValidationError
from bson import ObjectId
from datetime import datetime
from drivers_bp.events import *

drivers = Blueprint('drivers', __name__, template_folder='drivers_templates', url_prefix='/drivers')

# protect entire blueprint with login required and role required
@drivers.before_request
@roles_required(['driver'], fallback_endpoint='inter.account.setup_driver_profile')
def ensure_routes_protected():
    pass


@drivers.before_request
def check_active_ride():
    active_rider_request = rider_requests.find_one({ "$or": [{'driver_id':current_user.id}, {'rider_id':current_user.id}], 'status':'accepted'},)

    # check if user is driver or rider and find active ride, if active ride redirect to chat
    if active_rider_request:
        if active_rider_request['rider_id'] == current_user.id:
            return resolve_redirect(url_for('inter.chat.rider', ride_request_id=active_rider_request['_id']))
        else:
            return resolve_redirect(url_for('inter.chat.driver', ride_request_id=active_rider_request['_id']))

@drivers.get('')
def index():
    # get current driver data
    current_driver_data = driver_data.find_one({'user_id': current_user.id})
    
    # check if driver data exists and driver has a ride option
    if not current_driver_data or not current_driver_data.get('ride-option'):
        return resolve_redirect(url_for('inter.account.setup_driver_profile'))
    
    # check if driver has bank details otherwise redirect to wallet and notify to add bank details
    if not current_driver_data.get('bank'):
        flash('Please add your bank details to receive payments before accepting rides', 'warning')
        return resolve_redirect(url_for('inter.account.wallet'))
    
    # get the ride option data of the current driver
    current_driver_ride_option = current_driver_data['ride-option']
    ride_option_data = ride_options.find_one({'id': current_driver_ride_option})

    if not ride_option_data:
        return resolve_redirect(url_for('inter.account.setup_driver_profile'))

    # get available riders for the current driver ride option
    available_riders = list(rider_requests.find({'status': 'pending', 'ride_option': current_driver_ride_option, 'rider_id': {'$ne': current_user.id}, 'driver_id': {'$exists': False}}).sort('created_at', -1).limit(10))
    
    # add user obj to each rider request for methods and attributes
    for ride_request in available_riders:
        user = User.get_by_id(ride_request.get('rider_id'))
        ride_request['user'] = user

    resp = make_response(render_template('drivers_index.html', available_riders=available_riders, ride_option=current_driver_ride_option))

    resp.set_cookie('locale', str(get_locale()), httponly=True)
    return resp

@drivers.post('/accept/<ride_request_id>')
@htmx_request
def accept_ride(ride_request_id):
    try:
        ride_request_id = ObjectId(ride_request_id)
        ride_request = rider_requests.find_one({'_id': ride_request_id})

        if not ride_request or ride_request.get('status') != 'pending':
            raise ValidationError('Ride request not found')
        
        # update ride request status to accepted and add driver id
        rider_requests.update_one({'_id': ride_request_id}, {'$set': {'status': 'accepted', 'driver_id': current_user.id, 'accepted_at': datetime.now()}})

        # notify rider that their ride has been accepted, they will be redirected to chat using js
        socketio.emit('ride-accepted', {'redirect_url': url_for('inter.chat.rider', ride_request_id=ride_request_id)}, namespace='/riders', room=str(ride_request_id))

        # notify all drivers of this ride option that a ride has been accepted
        socketio.emit('ride-accepted', {'ride_request_id': str(ride_request_id), 'message':_('No Riders available at the moment')}, namespace=f'/drivers', room=ride_request['ride_option'])


        resp = make_response(render_template('accept-ride.html', ride_request_id=ride_request_id))
        
        return resp

    except ValidationError:
        return notify_accept_error_modal('Ride request not found', header="Ride Request Not Found", code=CODES.NOT_FOUND)
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request, current_user:current_user})
        return notify_accept_error_modal('We are currently unable to process you request. Please try again later', header="Server Error", code=CODES.INTERNAL_SERVER_ERROR)

   
