from flask import Blueprint, render_template, url_for, flash, request
from flask_login import current_user
from flask_babelex import get_locale
from bson import ObjectId
from datetime import datetime
from utils.mongo  import driver_data, ride_options
from utils.models import User
from utils.helper import resolve_redirect, roles_required, logging
from utils.notifications import notify_accept_error_modal
from utils.codes import CODES
from admin_bp.events import *

admin = Blueprint('admin', __name__, url_prefix='/admin', template_folder='admin_templates')

# NOTE dashboard is binded to app, but registered to blueprint using the custom_bp option in the bind function

@admin.before_request
@roles_required(['admin'])
def before_request():
    """ make sure user is an admin before accessing any admin route """
    pass

@admin.after_request
def set_socket_locale(response):
    response.set_cookie('socket_locale', str(get_locale()), httponly=True)
    return response


@admin.route('')
def index():
    return resolve_redirect(url_for('inter.admin.dashboard.index'))

@admin.route('/verify-drivers') # get unique drivers
def verify_drivers():

    """ view all drivers"""

    try:

        handle = request.args.get('handle', 'requests') # get the handle from the query string, default to requests
        if handle not in ('requests', 'history'): 
            handle = 'requests'

        all_drivers = None

        if handle == 'requests':
            # get all pending driver applications
            all_drivers = list(driver_data.find({'status': 'pending'}).sort('date_added', -1))
        else:
            # get all accepted and rejected driver applications
            all_drivers = list(driver_data.find({'status':{ '$in': ['accepted', 'rejected']}}).sort('handled_at', -1))

        if all_drivers:
            #  add the user object to each driver application to access methods and properties
            for driver in all_drivers:
                driver['user'] = User.get_by_id(driver['user_id'])

        return render_template('admin_verify-drivers.html', 
            all_drivers=all_drivers,
            handle=handle
        )
    
    except Exception as e:

        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        
        if 'hx-request' in request.headers:
            return notify_accept_error_modal('Unable to process request', 'Server Error')
        
        flash('Currently unable to process this request', 'error')
        return resolve_redirect(url_for('inter.admin.dashboard.index')), CODES.BAD_REQUEST


@admin.get('/verify-driver/<driver_id>')
def view_driver_application(driver_id):

    """ view a driver application"""

    try:
        # get the driver application
        driver_obj_id = ObjectId(driver_id)
        driver_application = driver_data.find_one({'_id': driver_obj_id})

        if not driver_application:
            raise Exception('Driver application not found')
        
        # add the user object to the driver application to access methods and properties
        driver_application['user'] = User.get_by_id(driver_application['user_id'])

        # get the ride option
        ride_option = ride_options.find_one({'id': driver_application['ride-option']})
        
        if not ride_option:
            raise Exception('Ride option not found')


        admin_handler=None
        if driver_application['status'] in ['accepted', 'rejected']:
            # get the admin handler
            admin_handler = User.get_by_id(driver_application['handled_by'])
        
            if not admin_handler: # all accepted and rejected driver applications should have an admin handler
                raise Exception('Admin handler not found')
        
        return render_template('driver-application.html', driver_application=driver_application, ride_option=ride_option, admin_handler=admin_handler)
        
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        if 'hx-request' in request.headers:
            return notify_accept_error_modal('Driver application not found', 'Not found', CODES.NOT_FOUND)
        
        flash('Driver application not found', 'error')
        return resolve_redirect(url_for('inter.admin.verify_drivers'))
    
@admin.post('/verify-driver/<driver_id>/accept', endpoint='accept_driver_application')
@admin.post('/verify-driver/<driver_id>/reject', endpoint='reject_driver_application')
def handle_driver_application(driver_id):
    """ accept or reject a driver application """
    try:
        # get the driver application and make sure it is pending
        driver_obj_id = ObjectId(driver_id)
        driver_application = driver_data.find_one({'_id': driver_obj_id, 'status': 'pending'})

        if not driver_application:
            raise Exception('Driver application not found')
        
        # check if the endpoint is accept or reject 
        if request.endpoint == 'inter.admin.accept_driver_application':
            driver_application['status'] = 'accepted' # update the status to accepted
            driver_user = User.get_by_id(driver_application['user_id'])
            driver_user.add_role('driver') # add the driver role to the user
        else:
            driver_application['status'] = 'rejected' # update the status to rejected

        # set handled_at and handled_by information for the driver application
        driver_application['handled_at'] = datetime.now()
        driver_application['handled_by'] = current_user.id

        # update the driver application
        driver_data.update_one({'_id': driver_obj_id}, {'$set': driver_application})

        # emit an event to the admin interface to update the driver application for all connected admins
        socketio.emit('driver-application-handled', {
            'driver_application_id': driver_id
        }, namespace='/admin')

        flash('Driver application has been {} successfully'.format(driver_application['status']), 'success')
        return resolve_redirect(url_for('inter.admin.verify_drivers'))

    except Exception as e:
        # print(e)
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        if 'hx-request' in request.headers:
            return notify_accept_error_modal('We are currently unable to process this request', 'Bad request')
        
        flash('We are currently unable to process this request', 'error')
        return resolve_redirect(url_for('inter.admin.verify_drivers')),