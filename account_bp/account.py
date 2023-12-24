from flask import Blueprint, render_template, abort, request, make_response, flash, url_for, send_file, current_app
from flask_login import current_user
from flask_babelex import gettext as _
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge, UnsupportedMediaType
from pymongo import ReturnDocument
from pathlib import Path
import json
from bson import ObjectId
from io import BytesIO
from datetime import datetime
from auth_bp.auth_helper import send_verification_code_email, validate_email_code
from account_bp.forms import UpdateEmailForm, UpdatePhoneForm, SetPasswordForm, UpdateNameForm, ProfilePhotoForm, AddPayPalForm, AddCardForm, DriverSetupForm, AddBankForm
from utils.codes import CODES
from utils.helper import resolve_redirect, htmx_request, roles_required, logging
from utils.config import Config
from utils.models import User
from utils.mongo import payment_methods, driver_data, gridfs, ride_options, rider_requests
from utils.extensions import socketio, redis_client
from utils.notifications import notify_accept_error_modal, notify
from account_bp.account_helper import send_receipt, verify_paymethod, sort_paymethods
from flask_babelex import gettext as _

account = Blueprint('account', __name__, template_folder='account_templates', url_prefix='/account')


# ========== Account wallet ==================  
@account.get('/wallet')
@roles_required(['driver', 'rider'])
def wallet():

    """ display all user payment methods """
    # get all user payment methods and sort them
    user_paymethods = list(payment_methods.find({'user_id': current_user.id, 'status': {'$ne': 'deleted'}}))
    user_paymethods = sorted(user_paymethods, key=sort_paymethods)
    driver_bank = None

    # get driver bank account if user is a driver
    if current_user.has_role('driver'):
        driver_bank = driver_data.find_one({'user_id': current_user.id}, {'_id':0, 'bank': 1})
        driver_bank = driver_bank.get('bank')

    return render_template('wallet.html', user_paymethods=user_paymethods, driver_bank=driver_bank)

@account.get('/wallet/add')
@roles_required(['driver', 'rider'])
@htmx_request
def add_payment_method():
    """ display the add payment method modal """
    return render_template('htmx/modals/add-paymethod-modal.html')

@account.route('/wallet/add/<string:method>', methods=['GET', 'POST'])
@roles_required(['driver', 'rider'])
@htmx_request
def add_payment_method_type(method):

    """ add a payment method to the user: 
    constraints: 
            can only add up to 6 payment methods
            can only paypal or card
    """

    if method not in ('paypal', 'card'):
        return abort(CODES.NOT_FOUND)
    
    # get user payment methods count
    user_payment_methods = payment_methods.count_documents({'user_id': current_user.id, 'status': {'$ne': 'deleted'}})

    # check if user has 6 payment methods, if so, display a warning for both post and get requests
    if user_payment_methods == 6:
        return  make_response(render_template('htmx/modals/add-paymethod-modal.html', exceed_warning=True))
    
    # display the add payment method modal with the relevant form
    if method == 'paypal':
        form = AddPayPalForm()
    else:
        form = AddCardForm()
    
    if request.method == 'GET':
    
        # display the add payment method modal with the relevant form and trigger js handleCustomInputs
        resp = make_response(render_template('htmx/modals/add-paymethod-modal.html', form=form, method=method))
        resp.headers['HX-Trigger-After-Swap'] = json.dumps({ 'handleCustomInputs': '', 'linkInputsToNext': ''})
        return resp
    
    # handle the form submission to display any errors
    if not form.validate_on_submit():
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.BAD_REQUEST
    
    # validate the form data to check if the user already has a paypal account with the same email or a card with the same number
    validated = True
    if method == 'paypal':
        # check if user already has a paypal account with the mail
        if payment_methods.count_documents({'user_id': current_user.id, 'method': 'paypal', 'email': form.email.data}) > 0:
            validated=False
            message = _('You already have a PayPal account with this email')

    elif method == 'card':
        # check if user already has a card with the same number
        if payment_methods.count_documents({'user_id': current_user.id, 'method': 'card', 'card_number': form.card_number.data}) > 0:
            message = _('You already have a card with this number')
            validated=False
    
    # notify the user if the form data is not valid
    if not validated:
        return notify(message=message, type='warning')
    
    # remove the csrf token and add button from the form data
    relevant = {k: v for k, v in form.data.items() if k not in ('csrf_token', 'add')}

    # merge the form data with the user id and date added and method, star the method if it is the first payment method
    to_insert = {'user_id': current_user.id, 'method': method, 'date':datetime.now(), 'is_starred':user_payment_methods==0} | relevant
    payment_methods.insert_one(to_insert) # insert the payment method to the database

    # get all user payment methods and sort them
    new_user_paymethods = payment_methods.find({'user_id':current_user.id, 'status':{'$ne':'deleted'}})
    new_user_paymethods = sorted(new_user_paymethods, key=sort_paymethods)

    # display the add payment method modal with the success message and the new payment methods
    resp = make_response(render_template('htmx/modals/add-paymethod-modal.html', success=True, method=method, user_paymethods=new_user_paymethods))
    return resp


@account.route('/payment-method/<string:paymethod>', methods=['GET', 'PATCH'])
@roles_required(['driver', 'rider'])
def handle_payment_method(paymethod: ObjectId):
    
    """ handles displaying a single payment method and also starring it """
    paymethodId, handled_paymethod = verify_paymethod(paymethod=paymethod)
    if not paymethodId or not handled_paymethod:
        flash('An error occured', 'error')
        return resolve_redirect(url_for('inter.account.wallet'))
    
    if request.method == 'PATCH':
        if 'hx-request' not in request.headers:
            return {}, CODES.NO_CONTENT
        
        # star the selected payment method and unstar the rest
        handled_paymethod = payment_methods.find_one_and_update({'user_id': current_user.id, '_id':paymethodId}, {'$set': {'is_starred': True}}, return_document=ReturnDocument.AFTER)
        payment_methods.update_many({'user_id': current_user.id, '_id': {'$ne': paymethodId}}, {'$set': {'is_starred': False}})
        
    # display the selected payment method
    return render_template('single-payment-method.html', paymethod=handled_paymethod)


@account.route('/payment-method/<string:paymethod>/remove', methods=['GET', 'DELETE'])
@roles_required(['driver', 'rider'])
@htmx_request
def remove_payment_method(paymethod: ObjectId):

    """ remove a payment method from the user, if the removed paymethod is starred, star the first paymethod"""
    paymethodId, handled_paymethod = verify_paymethod(paymethod=paymethod)
    if not paymethodId or not handled_paymethod:
        flash('An error occured', 'error')
        return resolve_redirect(url_for('inter.account.wallet'))
    
    if request.method == 'GET':
        #  show confirmation modal and display a different message if the paymethod is the only paymethod besides cash
        if payment_methods.count_documents({'user_id': current_user.id, '_id': paymethod, 'method': {"$ne":'cash'}}) == 1:
            message = _("Are you sure you want to remove your only other payment method?")
        else:
            message = _("Are you sure you want to remove this payment method?")
        
        return render_template('account_htmx/remove-paymethod-modal.html', paymethodId=paymethodId, message=message, confirmation=True)
    
    # remove the payment method - update it to be removed so that it is not deleted from the database this way we can still access it for receipts/trip data
    deleted_paymethod = payment_methods.update_one({'user_id': current_user.id, '_id': paymethodId, "method": {"$ne":'cash'}}, {'$set': {'is_starred': False, 'status': 'deleted', 'date_deleted': datetime.now()}})

    # if the paymethod was not removed, display an error message
    if deleted_paymethod.modified_count == 0:
        return render_template('htmx/modals/remove-paymethod-modal.html', del_error=True, paymethod=paymethod, message="Currently unable to remove this payment method")
    
    # if the removed paymethod is starred, star the first paymethod
    if handled_paymethod.get('is_starred'):
        # get all user payment methods
        user_payment_methods = list(payment_methods.find({'user_id': current_user.id, 'status': {'$ne':'deleted'}}))
        if len(user_payment_methods) > 0:
            # get the first payment method
            starred_paymethod = user_payment_methods[0]

            # update the first payment method to be starred
            payment_methods.update_one({'user_id': current_user.id, '_id': starred_paymethod['_id']}, {'$set': {'is_starred': True}})

    # refresh the wallet page
    flash(_('Payment method removed'), 'success')
    return resolve_redirect(url_for('inter.account.wallet'))

@account.route('add-bank', methods=['GET', 'POST'])
@roles_required(['driver'])
@htmx_request
def add_bank():

    """ add a bank account for a driver """
    driver_bank = driver_data.find_one({'user_id': current_user.id}, {'_id':0, 'bank': 1})

    form = AddBankForm()    
    if request.method == 'GET':

        # if the driver already has a bank account, display a warning
        if driver_bank:
            return render_template('account_htmx/add-bank-account-modal.html', exceed_warning=True)
        
        resp  = make_response(render_template('account_htmx/add-bank-account-modal.html', form=form))
        resp.headers['HX-Trigger-After-Swap'] = json.dumps({ 'handleCustomInputs': '', 'linkInputsToNext': ''})
        return resp
    
    if not form.validate_on_submit():
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.BAD_REQUEST
    
    if driver_bank:
        # if the driver already has a bank account, display a warning and configure headers for retargeting and reselecting
        resp = make_response(render_template('account_htmx/add-bank-account-modal.html', exceed_warning=True))
        resp.headers['HX-Retarget'] = '#modal-bg'
        resp.headers['HX-Reswap'] = 'outerHTML'
        resp.headers['HX-Reselect'] = '#modal-bg'
        return resp

    # remove the csrf token and add button from the form data
    relevant = {k: v for k, v in form.data.items() if k not in ('csrf_token', 'add')}

    # merge the form data with the balance default set to 0 and the current date
    added_data =  relevant | {'balance':0, 'date_added': datetime.now()}

    # add the bank account to the driver data
    driver_data.update_one({'user_id': current_user.id}, {'$set': {'bank': added_data}})

    return render_template('account_htmx/add-bank-account-modal.html', success=True, driver_bank=added_data)



# ================== Manage account ====================
@account.get('/security', endpoint='security') # use endpoint to avoid conflict for updating display indicator
@account.get('')
@roles_required(['driver', 'rider'])
def manage():
    """ manage account information """
    photo_form = ProfilePhotoForm()
    return render_template('manage.html', photo_form=photo_form)

@account.get('/update/<string:resource>')
def update(resource):
    """ update account information """

    # check if the resource is valid
    if resource not in ('email', 'phone', 'name', 'password'):
        return abort(CODES.NOT_FOUND)
    
    # get the relevant form and header for the resource
    # method is used for the form action, default is patch for all resources except email and if setting password for the first time
    method = 'PATCH'
    if resource == 'email':
        form = UpdateEmailForm(email=current_user.email)
        header = 'Update Email'
        method='POST' # email is updated using post

    elif resource == 'phone':
        form = UpdatePhoneForm(phone=current_user.phone)
        header = _('Update Phone Number')

    elif resource == 'name':
        form = UpdateNameForm(fname=current_user.fname, lname=current_user.lname)
        header = _('Update Name')

    elif resource == 'password':
        is_reset = current_user.password is not None

        if not is_reset: 
            method = 'POST'
        else:
            resource = 'reset_password'

        form = SetPasswordForm(is_reset=is_reset)
        header = _('Update Password') if is_reset else _("New Password")

    resp = make_response(render_template('update.html', form=form, resource=resource, header=header, method=method))
    resp.headers['HX-Trigger'] = 'handleCustomInputs'
    return resp

@account.post('/update/email')
@roles_required(['driver', 'rider'])
def update_email():
    """ handle post for updating email"""
    form = UpdateEmailForm()

    # check if the form is valid
    if not form.validate_on_submit():
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.UNAUTHORIZED

    # check if the email is the same as the current email
    form_email = form.email.data
    if form_email == current_user.email:
        flash(_('No changes to be made', 'warning'))
        return resolve_redirect(url_for('inter.account.manage'))
    
    # send the verification code to the user to be valdiated if they can access the email
    return send_verification_code_email(form_email, 
                                        action=url_for('inter.account.validate_code_update_email'), 
                                        start_url=url_for('inter.account.manage'), 
                                        template_message=_("Enter this code to update your email address"),
                                        template_header=_("Update you email address"),
                                        is_user=True)

@account.post('/update/email/validate')
@roles_required(['driver', 'rider'])
def validate_code_update_email():
    """ validate the code sent to the user to update their email address """
    # validate the code
    validated, resp = validate_email_code(action=url_for('inter.account.validate_code_update_email'))
    if not validated:
        return resp
    
    current_user.update_email(resp)

    flash(_('Email updated successfully'), 'success')
    return resolve_redirect(url_for('inter.account.manage'))

@account.patch('/update/phone')
@roles_required(['driver', 'rider'])
def update_phone():
    """ update user phone number """
    form = UpdatePhoneForm()
    if not form.validate_on_submit():
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.UNAUTHORIZED
        
    # update the user phone number
    current_user.update_phone(form.phone.data)

    flash(_('Phone number updated successfully'), 'success')
    return resolve_redirect(url_for('inter.account.manage'))


@account.patch('/update/name')
@roles_required(['driver', 'rider'])
def update_name():

    """ update user name """
    form = UpdateNameForm()
    if not form.validate_on_submit():
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.UNAUTHORIZED
    current_user.update_name(form.fname.data, form.lname.data)

    flash(_('Name updated successfully'), 'success')
    return resolve_redirect(url_for('inter.account.manage'))


@account.patch('/update/reset-password', endpoint='update_reset_password')
@account.post('/update/password')
@roles_required(['driver', 'rider'])
@htmx_request
def update_password():
    """ update user password or set password for the first time """

    is_reset = request.method == 'PATCH'

    # render the set password form based on if it is an set or reset
    form = SetPasswordForm(is_reset=is_reset)

    if not form.validate_on_submit():
        # print('Error @ update_password form')
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.UNAUTHORIZED

    
    if is_reset:
        # chekc if the old password is the same as the new password
        if current_user.check_password(form.password.data):
            # print('Error @ update_password validate old passwowrd')
            return notify(message=_("No changes to be made"), type="warning", code=CODES.OK)
            # return render_template('htmx/notif.html', message=_("No changes to be made"), type="warning"), CODES.UNAUTHORIZED
        
        # validate the old password
        if not current_user.check_password(form.old_password.data):
            # print('Error @ update_password vlaidate old passwowrd')
            return notify(message=_("The old password is inccorrect"), type="error", code=CODES.BAD_REQUEST)
            # return render_template('htmx/notif.html', message=_("The old password is inccorrect"), type="error"), CODES.UNAUTHORIZED

    # update the user password
    current_user.set_password(form.password.data)
    flash(_('Password updated successfully'), 'success')
    return resolve_redirect(url_for('inter.account.security'))


@account.route('/update/photo', methods=['POST', 'DELETE'])
@roles_required(['driver', 'rider'])
@htmx_request
def update_profile_pic():
    """ update user profile picture  or remove it"""
    if request.method == 'DELETE':
        if current_user.has_role('driver'):
            # if user is a driver, they cannot remove their profile photo since it is used for their driver profile and is required
            return notify_accept_error_modal(_('You cannot remove your profile photo as a driver'), _('Unable to remove profile photo'), CODES.BAD_REQUEST)
        
        # remove the profile photo
        current_user.update_profile_pic(False)
        flash(_('Profile Photo removed'), 'success')
        return resolve_redirect(url_for('inter.account.manage'))

    # check if the file is in the request
    file = request.files.get('photo')

    # in file dont do anything
    if not file:
        return {}, CODES.NO_CONTENT
    
    form = ProfilePhotoForm()

    # validate the form and media  
    if not form.validate_on_submit():
        return notify(message=_('Invalid File Type'), type='error', code=CODES.UNSUPPORTED_MEDIA_TYPE)

    # save the file to the user profile folder
    output = Path(Config.UPLOAD_FOLDER) / current_user.build_path('profile', f'profile.png')
    output.parent.mkdir(exist_ok=True, parents=True)
    file.save(output)
    current_user.update_profile_pic(True)

    #  refresh the page and display the new profile photo
    flash(_('Profile Updated'), 'success')
    return resolve_redirect(url_for('inter.account.manage'))

# SET UP DRIVER PROFILE BEFORE DRIVING:
@account.route('/driver/setup', methods=['GET', 'POST'])
@roles_required(['driver', 'rider'])
def setup_driver_profile():

    # check if user is already a driver, if so redirect to driver profile or 
    if current_user.has_role('driver'):
        return resolve_redirect(url_for('inter.account.view_driver_profile'))
    
    # check if user already has a pending driver profile request, if so display pending page if method is get or display error if method is post
    if driver_data.count_documents({'user_id': current_user.id, 'status': 'pending' }) > 0:
        if request.method == 'GET':
            return render_template('manage.html', pending=True)
        else:
            if 'hx-request' in request.headers:
                return notify(message='You already have a pending driver profile request', type="warning", code=CODES.BAD_REQUEST)
            
            flash('You already have a pending driver profile request', 'warning')
            return resolve_redirect(url_for('inter.account.manage'))
    
    form = DriverSetupForm()
    if request.method == 'GET':
        # get all ride options to display in the form for the driver to select their ride type
        options = list(ride_options.find())
        context = {'form': form, 'options': options}
        return render_template('manage.html', **context)
    
    try:
        if not form.validate_on_submit():
            return render_template('htmx/form-errors.html', errors=form.errors), CODES.BAD_REQUEST
        
        # check if user has a profile photo, if not display error
        if not current_user.profile_pic:
            return notify_accept_error_modal(message=_('Please add a profile photo before going ahead!'), header=_('Bad Request'), code=CODES.BAD_REQUEST)
        # if no ride option is selected, display error
        if not request.form.get('ride-option'):
            return notify(message=_('Please select a ride option'), type='warning'), CODES.BAD_REQUEST
           
        # remove the csrf token from the form data
        added_data = {k: v for k, v in request.form.items() if k not in ('csrf_token') and v}
        
        # get the license and vehicle photos from the request
        license_photo = request.files.get('license_photo')
        vehicle_photo = request.files.get('vehicle_photo')
        if not request.files or not license_photo or not vehicle_photo: 
            # if no files are in the request, display error
            return notify(message=_('Both photos are required'), type='warning'), CODES.BAD_REQUEST
           
        # save the license and vehicle photos to the database using gridfs
        license_file_id = gridfs.put(license_photo, filename=secure_filename(license_photo.filename), content_type=license_photo.content_type, user_id=current_user.id)
        vehicle_file_id = gridfs.put(vehicle_photo, filename=secure_filename(vehicle_photo.filename), content_type=vehicle_photo.content_type, user_id=current_user.id)
        
        # add files to data to add to the db
        user_driver_data = {'user_id':current_user.id,  'status':'pending', 'date_added': datetime.now(), 'license_photo': license_file_id, 'vehicle_photo': vehicle_file_id} | added_data
        
        # insert the driver data to the database and get the inserted id
        res_id = driver_data.insert_one(user_driver_data)
        driver = driver_data.find_one({'_id': res_id.inserted_id})

        # set the user for the driver data for jinja to use methods and user attributes
        driver['user'] = current_user

        flash(_('Driver profile requested successfully'), 'success')
        resp = make_response(resolve_redirect(url_for('inter.account.view_driver_profile')))
        resp.headers['HX-Trigger-After-Swap'] = json.dumps({'linkInputsToNext': '', 'initDatePickers':''})

        # send notification to admin that a valid driver profile request has been made
        admins = redis_client.smembers('admins')
        print(admins, 'admins')
        for admin in admins:
            sid, locale = admin.split(':')
            with current_app.test_request_context() as ctx:
                ctx.babel_locale = locale
                socketio.emit('driver-application-request-send', {'template': render_template('partials/driver-application-request.html', driver=driver)}, namespace='/admin', room=sid)
        
        # socketio.emit('driver-application-request-send', {'template': render_template('partials/driver-application-request.html', driver=driver)}, namespace='/admin')

        return resp
    
    except RequestEntityTooLarge as retl:
        logging.error(f"ERROR (RETL) @ {request.endpoint}: {retl}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        return notify(_("File too large (max: 10mb)"), 'error', code=CODES.CONTENT_TOO_LARGE)
    
    except UnsupportedMediaType as umt:
        logging.error(f"ERROR (UMT) @ {request.endpoint}: {umt}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        return notify( message =_("Invalid File Type") , type='error', code=CODES.UNSUPPORTED_MEDIA_TYPE)
    
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        return notify(message =_("Currently unable to process your request") , type='error', code=CODES.BAD_REQUEST)

@account.get("/driver")
@roles_required(['driver'], fallback_endpoint='inter.account.setup_driver_profile')
def view_driver_profile():

    """ view a driver profile for the current user"""
    driver_profile = driver_data.find_one({'user_id':current_user.id, 'status': 'accepted'})
    # if for some reason profile is not found and user has driver permission, then that is considered an anomoly
    is_htmx = 'htmx_request' in request.headers
    if not driver_profile:
        if is_htmx:
            return notify_accept_error_modal(_('Driver profile not found'), _('Not Found'), CODES.NOT_FOUND)
        else:
            flash(_('Driver profile not found'), 'error')
            return resolve_redirect(url_for('inter.account.setup_driver_profile'))
        
    # get the ride option name to display on the driver profile
    ride_option = ride_options.find_one({'id': driver_profile['ride-option']})
        
    return render_template('manage.html', driver_profile=driver_profile, ride_option=ride_option)

def return_photo(driver, file_id):
    """ return a photo from the database using gridfs """
    file = gridfs.find_one({"_id": ObjectId(file_id), 'user_id': driver})

    if not file:
        return abort(CODES.NOT_FOUND)

    data = file.read()
    response = BytesIO(data)
    
    return send_file(response, mimetype=file.content_type)

@account.get('/driver/<int:driver>/license/<string:file_id>')
@roles_required(['driver', 'admin']) # allow only the driver of this photo or all admins to view
def view_driver_license(driver, file_id):
    """ view a driver license photo """
    if not current_user.has_role('admin'):
        # if user is not an admin, check if they are the driver of this photo
        if not current_user.id == driver:
            return abort(CODES.UNAUTHORIZED)
     
    return return_photo(driver, file_id) # get and return the photo

@account.get('/driver/<int:driver>/vehicle/<string:file_id>')
def view_driver_vehicle(driver, file_id):
    # allow anyone to view this photo no roles required
    return return_photo(driver, file_id)


# ==== Simplified account settings =========
@account.get('/settings')
@roles_required(['driver', 'rider'])
def settings():
    # display the settings page
    return render_template('settings.html')


# ====== Account trips ===========
# ===== trips for both riders and drivers
@account.get('/trips')
@roles_required(['driver', 'rider'])
def trips():
    """ view all completed trips for the user"""
    
    riding = request.args.get('riding', 'rider') # get the riding query param, default is rider
    if riding not in ('rider', 'driver'):
        riding = 'rider'

    all_trips = None

    # get all trips for the user based on the riding query param
    if current_user.has_role('driver') and riding == 'driver':
        all_trips = list(rider_requests.find({'driver_id': current_user.id, 'status': 'completed'}).sort('accepted_at', -1))
    else:
        all_trips = list(rider_requests.find({'rider_id': current_user.id, 'status': 'completed'}).sort('accepted_at', -1))

    return render_template('trips.html', all_trips=all_trips, riding=riding)

@account.get('/trip/<string:ride_id>')
@roles_required(['driver', 'rider'])
def trip_details(ride_id):

    """ view the details of a specific trip """

    try:
        # get the completed trip and check if the user is a member of the trip
        trip = rider_requests.find_one({'_id': ObjectId(ride_id), 'status': 'completed', '$or': [{'rider_id': current_user.id}, {'driver_id': current_user.id}]})
        if not trip:
            return abort(CODES.NOT_FOUND)
        
        # get the ride option name to display on the trip details
        trip['ride_option_name'] = ride_options.find_one({'id': trip['ride_option']}, {'_id':0, 'name':1})['name']
        trip['formatted_distance'] = f"{trip['distance']/1000:.2f} km" # format the distance to display on the trip details

        #  check if the user is a rider or driver
        is_rider = trip['rider_id'] == current_user.id

        trip['other_member'] = User.get_by_id(trip['driver_id']).fname if is_rider else User.get_by_id(trip['rider_id']).fname # get the other member of the trip 
        if not trip['other_member']:
            raise Exception('Unable to find other member')

        if is_rider:
            paymethod_data = payment_methods.find_one({'_id': trip['pay_method'], 'user_id':trip['rider_id']}, {'_id':0, 'method':1, 'card_number':1, 'email':1})
            if not paymethod_data:
                raise Exception('Payment method not found')
            
            if paymethod_data['method'] == 'paypal':
                trip['formatted_paymethod'] = f'PayPal: {paymethod_data["email"]}'
            elif paymethod_data['method'] == 'cash':
                trip['formatted_paymethod'] = 'Kuber Cash'
            else:
                trip['formatted_paymethod'] = _('Card') + ': xxxx-xxxx-xxxx-' + paymethod_data['card_number'][-4:]

        # get the duration of the trip since it is based on length of time of the chat
        duration = trip['ended_at'] - trip['accepted_at']
        duration_hours = duration.seconds // 3600
        duration_minutes = duration.seconds // 60

        if duration_hours > 6:
            trip['duration'] = _('6 hrs (maximum)') # if duration is more than 6 hrs, display 6 hrs as a default max
        elif duration_minutes == 0:
            trip['duration'] = _('3 minutes (minimum)') # if duration is 1 min,  display 3 mins as a default min
        else:
            trip['duration'] = f'{duration_minutes}' + ' ' + _('minutes') # display the duration in minutes

        
        return render_template('trip-details.html', trip=trip, is_rider=is_rider) 

    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        if 'hx-request' in request.headers:
            return notify_accept_error_modal(_('We are currently unable to process this request'), _('An error occured'), CODES.BAD_REQUEST)

        else:
            flash(_('We are currently unable to process this request'), 'error')
            return resolve_redirect(url_for('inter.account.trips'))
        

@account.post('/trip/<string:ride_id>/resend-receipt')
def resend_receipt(ride_id):

    """ resend the receipt of a specific trip to a rider or driver """

    try:
        # get the completed trip and check if the user is a member of the trip
        trip = rider_requests.find_one({'_id': ObjectId(ride_id), 'status': 'completed', '$or': [{'rider_id': current_user.id}, {'driver_id': current_user.id}]}) 
        if not trip:
            raise Exception('Trip not found')

        # send the receipt to the rider or driver based on who is requesting the receipt
        if trip['rider_id'] == current_user.id:
            send_receipt(ride_id, 'rider', is_update=False)
        elif trip['driver_id'] == current_user.id:
            send_receipt(ride_id, 'driver',is_update=False)
        else:
            raise Exception('Trip data error')
        
        return notify(message=_('Receipt resent successfully'), type='success')
        
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        if 'hx-request' in request.headers:
            return notify_accept_error_modal(_('We are currently unable to process this request'), _('An error occured'), CODES.BAD_REQUEST)

        else:
            flash(_('We are currently unable to process this request'), 'error')
            return resolve_redirect(url_for('inter.account.trips'))
        