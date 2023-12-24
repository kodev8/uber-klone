from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session, make_response, jsonify, current_app 
from flask_login import login_required, current_user
from flask_babelex import gettext as _
from utils.codes import CODES
from utils.helper import resolve_redirect, htmx_request, roles_required
from utils.notifications import notify_accept_error_modal, notify
from datetime import datetime
from utils.mongo import ride_options, payment_methods, rider_requests
from riders_bp.forms import RideForm, RideDetailsForm
from locations_bp.locations import find_route, calculate_fare, reverse_geocode
from wtforms.validators import ValidationError
from general_bp.forms import CustomDateField
from utils.extensions import socketio, redis_client
from bson import ObjectId
import json
from pymongo import ReturnDocument
from riders_bp.events import *
from account_bp.account_helper import sort_paymethods

riders = Blueprint('riders', __name__, template_folder='riders_templates', url_prefix='/riders')

# protect entire blueprint with login required
@riders.before_request
@roles_required(['rider'])
def check_searching():
    if rider_requests.find_one({'rider_id':current_user.id, 'status':'pending'}) and  'search' not in request.endpoint:
        return resolve_redirect(url_for('inter.riders.searching'))

@riders.before_request
def check_active_ride():
    active_rider_request = rider_requests.find_one({ "$or": [{'driver_id':current_user.id}, {'rider_id':current_user.id}], 'status':'accepted'},)

    # check if user is driver or rider
    if active_rider_request:
        if active_rider_request['rider_id'] == current_user.id:
            return resolve_redirect(url_for('inter.chat.rider', ride_request_id=active_rider_request['_id']))
        else:
            return resolve_redirect(url_for('inter.chat.driver', ride_request_id=active_rider_request['_id']))

@riders.get('')
def index():
    pickup = None
    dropoff = None
    pickup_details = None

    # only set pickup and dropoff if coming from details page
    if 'hx-request' in request.headers:
        pickup = request.args.get('pickup')
        dropoff = request.args.get('dropoff')
        pickup_details = request.args.get('pickup_details')

    form = RideForm(pickup=pickup, dropoff=dropoff, pickup_details=pickup_details or _("Pickup now"))
    resp = make_response(render_template('riders_index.html', form=form, content="index"))
    if 'hx-request' in request.headers: 
        resp.headers['HX-Trigger-After-Swap'] = json.dumps({'handleCustomInputs': '', 
                                                            'setMapWidth': {'width': 'grow'}, 
                                                            'initMap':{'fresh':request.headers.get('HX-Target') != 'rider-form' }, # only init map if not coming from ride form
                                                            'restoreBody':'',
                                                            'evalRideForm':''
                                                            })
    return resp

@riders.route('/details', methods=['GET', 'POST'])
@htmx_request
def details():

    pickup = request.args.get('pickup')
    dropoff = request.args.get('dropoff')

    now = datetime.now()
    rider_details_form = RideDetailsForm(pickup_date=now.strftime("%Y-%m-%d"),)

    # propagate pickup and dropoff locations to through url args to maintain state
    if request.method == 'GET':
        resp = make_response(render_template('riders_htmx/ride_details_form.html', form=rider_details_form, pickup=pickup, dropoff=dropoff))
        resp.headers['HX-Trigger-After-Swap'] ='initDatePickers'
        return  resp
    
    if not rider_details_form.validate_on_submit():
        # print("Failed at ride details form submit", rider_details_form.errors)
        return render_template('htmx/form_errors.html',errors=rider_details_form.errors)
    
    # strings converted to time and date objects in the rider form details validation checks
    # if the time is not now, then combine the date and time
    pickup_details = None
    if type(rider_details_form.pickup_time.data) != str:
        pickup_details = rider_details_form.pickup_date.data.strftime('%b %d') + rider_details_form.pickup_time.data.strftime(' at %I:%M %p')
    
    ride_form = RideForm(pickup=pickup, dropoff=dropoff, pickup_details=_("Pickup") + " "  + (pickup_details or _("now")))
    ride_form.pickup_details.render_kw = {'data-value': pickup_details or 'now'}

    resp = make_response( render_template('riders_index.html', form=ride_form, content='index'))
    resp.headers['HX-Trigger-After-Swap'] = 'evalRideForm'
    return resp

@riders.route('/update-ride-times', methods=['POST'])
@htmx_request
def update_times():
    date = request.form.get('pickup_date')
    try:
        # test if date is in given date format
        datetime.strptime(date, CustomDateField.date_format)
    except:
        return notify_accept_error_modal(_('Invalid date format'), _('Bad Request'), CODES.BAD_REQUEST)
        
    rider_details_form = RideDetailsForm(pickup_date=date)

    resp = make_response(render_template('riders_htmx/ride_details_form.html', form=rider_details_form))

    return  resp

@riders.route("/choose-ride")
def choose_ride():

    pickup = request.args.get('pickup')
    pickup_lat = request.args.get('pickup_lat')
    pickup_lon = request.args.get('pickup_lon')
    pickup_osm_id = request.args.get('pickup_osm_id')

    dropoff = request.args.get('dropoff')
    dropoff_lat = request.args.get('dropoff_lat')
    dropoff_lon = request.args.get('dropoff_lon')
    dropoff_osm_id = request.args.get('dropoff_osm_id')

    is_htmx = 'hx-request' in request.headers

    pickup_details = request.args.get('pickup_details')

    if not all([pickup, pickup_lat, pickup_lon, dropoff, dropoff_lat, dropoff_lon, pickup_details, pickup_osm_id, dropoff_osm_id]):
        flash('Missing info', 'warning')
        return resolve_redirect(url_for('inter.riders.index'))
    
    # check pickup details
    form = RideForm()
    form.pickup_details.data = pickup_details

    try:
        form.validate_pickup_details(field=form.pickup_details)
    except ValidationError:
        flash(_('Invalid pickup data'), 'warning')
        return resolve_redirect(url_for('inter.riders.index'))
    
    route = find_route(pickup_lat, pickup_lon, pickup_osm_id, dropoff_lat, dropoff_lon, dropoff_osm_id)

    pickup_data = reverse_geocode(pickup_lat, pickup_lon, pickup_osm_id)
    if not pickup_data:
        if is_htmx:
            return notify_accept_error_modal(_('Invalid pickup location'), _('Bad Request'), CODES.BAD_REQUEST)
        else:
            flash(_('Invalid pickup location'), 'warning')
            return resolve_redirect(url_for('inter.riders.index'))
         
    dropoff_data = reverse_geocode(dropoff_lat, dropoff_lon, dropoff_osm_id)
    if not dropoff_data:
        msg = _('Invalid dropoff location')
        if is_htmx:
            return notify_accept_error_modal(msg, _('Bad Request'), CODES.BAD_REQUEST)
        else:
            flash(msg, 'warning')
            return resolve_redirect(url_for('inter.riders.index'))
        
#  get ride options from mongo db
    context = {}
    if route:
        context['route'] = True

        recommended_options = list(ride_options.find({'ride_type':'recommended'}))
        popular_options = list(ride_options.find({'ride_type':'popular'}))
        more_options = list(ride_options.find({'ride_type':'more'})) 

        options = [*recommended_options, *popular_options, *more_options]
        
        # calculate fare for each option
        route_duration = route['routes'][0]['duration']
        route_distance = route['routes'][0]['distance']
        
        for option in options:
            option['price'] = calculate_fare(route_distance, route_duration, option)

        context['recommended_options'] = recommended_options
        context['popular_options'] = popular_options
        context['more_options'] = more_options
    

    context['exec_scripts'] = 'hx-request' not in request.headers
    starred_paymethod = payment_methods.find_one({'user_id':current_user.id, 'is_starred':True})
    context['starred_paymethod'] = starred_paymethod

    response = make_response( render_template(
                                            'riders_index.html', 
                                            content="choose-ride",
                                            pickup_data=pickup_data, 
                                            pickup_details=pickup_details,
                                            dropoff_data=dropoff_data,
                                            **context))
    if 'hx-request' in request.headers:
        # change map size
        headers = {
            'setMapWidth': {
                'width': 'shrink'
                },
            'drawRoute':{
                'pickup_lat':pickup_lat,
                'pickup_lon':pickup_lon,
                'dropoff_lat':dropoff_lat,
                'dropoff_lon':dropoff_lon,
                'pickup_osm_id':pickup_osm_id,
                'dropoff_osm_id':dropoff_osm_id,
              }
            }
        response.headers['HX-Trigger-After-Swap'] = json.dumps(headers)

    return response

@riders.route('/choose-ride/payment-method', methods=['GET'])
@htmx_request
def payment_method():
    user_paymethods = list(payment_methods.find({'user_id':current_user.id}))
    user_paymethods = sorted(user_paymethods, key=sort_paymethods)

    return render_template('riders_htmx/select-paymethod-modal.html', content="payment-method", user_paymethods=user_paymethods)
    
@riders.route('/choose-ride/payment-method', methods=['POST'])
@htmx_request
def payment_method_post():

    pay_method = request.form.get('pay_method')

    try:
        if not pay_method:
            raise ValueError(f'Invalid payment method: {pay_method}')
        
        
        pay_method_id = ObjectId(pay_method)
        pay_method_obj = payment_methods.find_one({'user_id':current_user.id, '_id':pay_method_id})

        if not pay_method_obj:
            raise ValueError(f'Invalid payment method: {pay_method}')
        
        resp = make_response(render_template('riders_htmx/update-paymethod.html', paymethod=pay_method_obj))
        resp.headers['HX-Trigger'] = 'closeModal'
        return resp

    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request, 'current_user':repr(current_user)})
        return notify(_('Invalid payment method'), 'warning', code=CODES.BAD_REQUEST)
       

@riders.post('/choose-ride/confirm-ride')
@htmx_request
def confirm_ride():

    pickup_lat = request.form.get('pickup_lat')
    pickup_lon = request.form.get('pickup_lon')
    pickup_osm_id = request.form.get('pickup_osm_id')

    dropoff_lat = request.form.get('dropoff_lat')
    dropoff_lon = request.form.get('dropoff_lon')
    dropoff_osm_id = request.form.get('dropoff_osm_id')

    pickup_details = request.form.get('pickup_details')

    pay_method = request.form.get('paymethod')
    ride_option = request.form.get('ride-option')

    try:
        route = find_route(pickup_lat, pickup_lon, pickup_osm_id, dropoff_lat, dropoff_lon, dropoff_osm_id) # should be cached at this point but also allows for testing

        if not all([pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, pickup_details, pay_method, ride_option]) or not route:
            raise ValidationError(_('Missing info'))
        
        pay_method_id = ObjectId(pay_method)
        verify_payment = payment_methods.find_one({'user_id':current_user.id, '_id':pay_method_id})
        if not verify_payment:
            raise ValidationError('Invalid payment method')
        
        verify_ride_option = ride_options.find_one({'id':ride_option})
        if not verify_ride_option:
            raise ValidationError('Invalid ride option')
        
            # check pickup details
        form = RideForm()
        form.pickup_details.data = pickup_details
        form.validate_pickup_details(field=form.pickup_details)

         # calculate how much the driver would make
        rider_price = calculate_fare(route['routes'][0]['distance'], route['routes'][0]['duration'], verify_ride_option, formatted=False)
        driver_price = rider_price * 0.75 #75% of rider price
        
        # rider_price = f"{rider_price:.2f}"
        # driver_price = f"{driver_price:.2f}"
        
        ride_request = {
            'pickup_lat':pickup_lat,
            'pickup_lon':pickup_lon,
            'pickup_osm_id':pickup_osm_id,
            'pickup_data':reverse_geocode(pickup_lat, pickup_lon, pickup_osm_id),
            'dropoff_lat':dropoff_lat,
            'dropoff_lon':dropoff_lon,
            'dropoff_osm_id':dropoff_osm_id,
            'dropoff_data':reverse_geocode(dropoff_lat, dropoff_lon, dropoff_osm_id),
            'pickup_details':pickup_details,
            'pay_method':pay_method_id,
            'ride_option':ride_option,
            'rider_id':current_user.id,
            'created_at':datetime.now(),
            'status':'pending', 
            'rider_price':rider_price,
            'driver_price':driver_price,
            'image':verify_ride_option['image'], # for displaying in trips
            'distance':route['routes'][0]['distance'],
        }

        # update pending requests that have the same data
        ride_request = rider_requests.find_one_and_update({'rider_id':current_user.id, 
                                                           'status':'pending', 
                                                           'pickup_osm_id':pickup_osm_id, 
                                                           'dropoff_osm_id':dropoff_osm_id,
                                                           'pickup_details':pickup_details,
                                                            'pay_method':pay_method_id,
                                                           }, {'$set':ride_request}, upsert=True, return_document=ReturnDocument.AFTER)

        ride_request['user'] = current_user

        # notify all drivers of new ride request
        socketio.emit('ride-request', {'template':render_template('notify-available.html', rider=ride_request)}, namespace=f'/drivers', room=ride_option)
        return resolve_redirect(url_for('inter.riders.searching'))
        
    except ValidationError as ve:
        return notify_accept_error_modal(ve, _('Invalid Data'), CODES.BAD_REQUEST)
    
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request, 'current_user':repr(current_user)})
        return notify_accept_error_modal(_('We are currently unable to process this request'), _('Bad Request'), CODES.INTERNAL_SERVER_ERROR)

@riders.get('/searching')
def searching():

    ride_request = rider_requests.find_one({'rider_id':current_user.id, 'status':'pending'})
    if not ride_request:
        return resolve_redirect(url_for('inter.riders.index'))
    
    return render_template('rider_search.html', ride_request_id=ride_request['_id'] )

@riders.post('/searching/cancel')
@htmx_request
def cancel_search():
    del_ride = rider_requests.find_one_and_delete({'rider_id':current_user.id, 'status':'pending'})
    if not del_ride:
        return notify(_('We are currently unable to process this request'), 'warning', code=CODES.INTERNAL_SERVER_ERROR)
    
    drivers = redis_client.smembers(f'ride_option:{del_ride["ride_option"]}')
    
    # force msgs to be in driver locale
    for driver in drivers:
        sid, locale = driver.split(':')
        with current_app.test_request_context() as ctx:
            ctx.babel_locale = locale
            socketio.emit('cancel-ride', {'ride_request_id': str(del_ride['_id']),'message': _('No available riders at this moment')}, namespace=f'/drivers', room=sid)
    
    
    # socketio.emit('cancel-ride', {'ride_request_id': str(del_ride['_id']), 'message': _('No available riders at this moment')}, namespace=f'/drivers', room=del_ride['ride_option'])
    flash('Search cancelled', 'info')
    return resolve_redirect(url_for('inter.riders.index'))
