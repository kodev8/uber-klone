from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from flask_login import login_user, logout_user, login_required, logout_user, current_user
from utils.codes import CODES
from utils.models import User
from auth_bp.forms import AuthForm, CodeForm, NameForm, LoginPasswordForm
from utils.helper import resolve_redirect, htmx_request
from utils.codes import CODES
from utils.mongo import payment_methods
from uuid import uuid4
from datetime import timedelta, datetime
import json
from utils.extensions import  redis_client
from auth_bp.emails import send_email_gmail
from utils.config import DRIVER_STATE
from urllib.parse import urlparse, parse_qs
from utils.notifications import notify
from auth_bp.auth_helper import send_verification_code_email, validate_email_code, get_auth_redis_data, remove_auth_session_data_code, auth_session_id_required

auth = Blueprint('auth', __name__, template_folder='auth_templates', url_prefix='/auth')

# @auth.before_request
# @jwt_required(optional=True)
# def already_logged_in():
#     print(request.endpoint)
#     if request.endpoint != 'auth.logout':
#         if get_jwt_identity():
#             return resolve_redirect(url_for('inter.riders.index'))
  
@auth.before_request
def invalidate_auth_session_id():
    """ invalidates the auth session id if it does not exist in redis """
    auth_session_id = request.headers.get('X-Auth-Session-Id')
    if auth_session_id:
        if not redis_client.exists(auth_session_id):
            session.pop(auth_session_id, None)

@auth.before_request     
def already_logged_in():
    """ checks if user is already logged in and redirects to the appropriate page """
    if request.endpoint != 'inter.auth.logout' and current_user.is_authenticated:
        if current_user.has_role('admin'):
            return resolve_redirect(url_for('inter.admin.dashboard.index'))
        return resolve_redirect(url_for('inter.riders.index'))
    
@auth.after_request
def after_request(response):   
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@auth.after_request
def add_triggers(response):

    """ add htmx triggers to the response """

    if 'X-Allow-Trigger' in response.headers:
        if "HX-Trigger-After-Swap" not in response.headers:
            response.headers['HX-Trigger-After-Swap'] = "handleCustomInputs"

        else:
            # update the trigger
            response.headers["HX-Trigger-After-Swap"] = json.dumps(json.loads(response.headers["HX-Trigger-After-Swap"]) | {"handleCustomInputs": None})

    return response

@auth.route('', methods=['GET', 'POST'])
def auth_flow():

    """ starts the authentication flow from one page to the next"""
    form = AuthForm()

    if request.method == 'GET':
        resp = make_response(render_template('flow.html', form=form, step=1))
        # redis_client.flushall()
        # session.clear()

        resp.headers['X-Allow-Trigger'] = True
        if 'hx-request' in request.headers:
            resp.headers['HX-Retarget'] = 'body'

        return resp
    
    if not form.validate_on_submit():
        # print('Failed by auth_flow: form.validate_on_submit()', form.errors)
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.UNAUTHORIZED
    
    email = form.email.data

     # check if user is already registered
    user = User.get_by_email(email)
    is_user = user != None

    # push to password page if user with admin role
    if is_user and user.has_role('admin'):
        form = LoginPasswordForm()
        inAuthSessionId = str(uuid4())

        session[inAuthSessionId] = {
        'email': email,
        }

        redis_data = {
            'email': email,
        }

        redis_client.hset(inAuthSessionId, mapping=redis_data)

        # set expiry for 15 minutes in redis
        redis_client.expire(inAuthSessionId, timedelta(minutes=15))

        # trigger setInAuthSessionId via js for all subsequent requests during auth flow
        resp = make_response(render_template("flow.html", form=form, step=4, user=user, admin=True))
        resp.headers["HX-Trigger-After-Swap"] = json.dumps({
            "setInAuthSessionId":{
                'inAuthSessionId': inAuthSessionId
            }, 
            "linkInputsToNext": None
        })
    
        resp.headers['X-Allow-Trigger'] = True
        return resp

    # check if driver by either next url or state
    # sent with params - swp to check if redirect should be to driver / setup driver
    swp = parse_qs(request.form.get('swp'))
    next = state = None
    try:
        next = urlparse(swp.get('next')[0])
        state = parse_qs(next.query).get('state')[0]
        next = next.path
    except:
        next = request.args.get('next')

    is_driver = next == url_for('inter.drivers.index') or state == DRIVER_STATE
    
    template_header = "Welcome To Uber" if not is_user else f"Welcome Back {user.fname}- Log in here"

    return send_verification_code_email(
                                        email, 
                                        start_url=url_for('inter.auth.auth_flow'),
                                        action=url_for('inter.auth.validate_code'),
                                        template_message="Enter this code on the signup page to continue.",
                                        template_header=template_header,
                                        is_user=is_user,
                                        is_driver=is_driver,
                                        next=next
                                        )

@auth.route('/login-password', methods=['GET', 'POST'])
@auth_session_id_required
def login_password():

    form = LoginPasswordForm()
    email = get_auth_redis_data("email")
    next = request.args.get('next', get_auth_redis_data('next'))
    user = User.get_by_email(email)

   

    # check also if user has a password else show a message
    if not email or not user:
        # print("Fail by no email or no user")
        return resolve_redirect(url_for('inter.auth.auth_flow'))

    if not user.password:
        # print("Failed by no password")
        return notify("You have not created a password yet, please log in with the verification code", "warning", headers={'HX-Trigger': "closeModal"})

    if request.method == "GET":
        resp = make_response(render_template("flow.html", form=form, step=4, user=user))
        resp.headers['HX-Trigger'] = "closeModal"
        resp.headers["HX-Trigger-After-Swap"] = json.dumps({"linkInputsToNext":None})
        resp.headers['X-Allow-Trigger'] = True
        return resp

    if not form.validate_on_submit():
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.UNAUTHORIZED

    # check if password is correct
    if not user.check_password(form.password.data):
        return notify("Incorrect password", "error"), CODES.UNAUTHORIZED
    
    # login user and remove the auth session data
    login_user(user)
    remove_auth_session_data_code(request.headers.get('X-Auth-Session-Id'))

    # if user is admin redirect to admin dashboard
    if user.has_role('admin'):
        return resolve_redirect(url_for('inter.admin.dashboard.index'))

    # redirect to next url based on if the user is driver or not
    is_driver = int(get_auth_redis_data("is_driver"))
    if not next:
        next_url = url_for('inter.drivers.index') if is_driver else url_for('inter.riders.index')

    resp = make_response(resolve_redirect(next_url))

    return resp

@auth.post('/register')
@auth_session_id_required
def register():

    form = NameForm()
    if not form.validate_on_submit():
        return render_template('htmx/form-errors.html', errors=form.errors), CODES.UNAUTHORIZED
    
    fname = form.fname.data
    lname = form.lname.data

    # get relevant auth session data
    email = get_auth_redis_data("email")
    is_driver = int(get_auth_redis_data('is_driver'))
    # email = 'k@k.co'
    user_check = User.get_by_email(email)

    # check if user is already registered
    if user_check:
        return redirect(url_for('inter.auth.login_password'))
    

   
    # create user
    user = User(fname=fname, lname=lname, email=email)
    user.add_role('rider')
    User.add_user(user)

    # create user cash payment method
    payment_methods.update_one(
    {'user_id': user.id, 'method': 'cash'},
    {'$set': {'date': datetime.now()}},
    upsert=True
    )
   

    # login user and remove the auth session data
    remove_auth_session_data_code(request.headers.get('X-Auth-Session-Id'))
    login_user(user)

    next_url = url_for('inter.drivers.index') if is_driver else url_for('inter.riders.index')
    response = make_response(resolve_redirect(next_url))
    # return login_user(response, user)
    return response


@auth.post('/validate-code')
@auth_session_id_required
def validate_code():

    """ validates the OTP sent via email"""


    validated, resp = validate_email_code(action=url_for('inter.auth.validate_code'))
    if not validated:
        return resp
    
    # check if user is already registered
    user = User.get_by_email(resp)
    form = NameForm()
    is_driver = int(get_auth_redis_data('is_driver'))

    if not user:
        resp = make_response(render_template('flow.html', form=form, step=3))
        resp.headers["HX-Trigger-After-Swap"] = json.dumps({"linkInputsToNext":None})
        return resp

    # login user and remove the auth session data
    remove_auth_session_data_code(request.headers.get('X-Auth-Session-Id'))
    login_user(user)

    # redirect to next url based on if the user is driver or not
    next_url = get_auth_redis_data('next')
    if not next_url:
        next_url = url_for('inter.drivers.index') if is_driver else url_for('inter.riders.index')

    # print("IN VCODE", next_url, is_driver)
        
    response = make_response(resolve_redirect(next_url))
    
    # return login_user(response, user)
    return response

@auth.get('/resend-code')
@auth_session_id_required
@htmx_request
def resend_code():

    """ sends the OTP again to the user's email"""

    # check if to send the code page
    with_page = request.args.get('with_page')

    # get email from redis session data
    session_data = get_auth_redis_data()
    email = session_data.get('email')
    code = session_data.get('code')

    if not email or not code:
        return render_template('htmx/notif.html', message="Unable to send verification code", type="error"), CODES.UNAUTHORIZED
    # send_email_test = True

    # try to send the email with the code and notify the user if it failed
    send_email_test = send_email_gmail(email, content=render_template('emails/verification-code.html',code=code), subject="Your Uber Verification Code")
    if not send_email_test:
        return render_template('htmx/notif.html', message="Unable to send verification code", type="error"), CODES.UNAUTHORIZED

    if with_page:
        flash("Verification code sent!", "success")
        template = render_template("flow.html", form=CodeForm(formdata=None), step=2)
    
    else:
        template = render_template('htmx/notif.html', message="Verification code sent!", type="success")
    
    resp = make_response(template)
    resp.headers['HX-Trigger'] = "closeModal"
    resp.headers['X-Allow-Trigger'] = True
    return resp

@auth.get('/confirm')
@auth_session_id_required
@htmx_request
def confirm_back():

    """ returns modal to confirm if to start over """
    return render_template('auth_htmx/confirm.html')

@auth.get('/verify-options')
@auth_session_id_required
@htmx_request
def verify_options():
    """ checks which options to show in the modal (login with password or code)"""
    with_password = request.args.get('with_password')
    with_code = request.args.get('with_code')
    return render_template('auth_htmx/code-options-modal.html', with_password=with_password, with_code=with_code)

@auth.delete('/logout')
@login_required
def logout():
    """ logs out the user and clears the session"""
    session.clear()
    logout_user()
    return resolve_redirect(url_for('inter.general.index'))

# step 2&3 https://flask-jwt-extended.readthedocs.io/en/stable/blocklist_and_token_revoking.html
# @auth.route("/logout", methods=["DELETE"])
# @jwt_required(optional=True)
# def logout():
#     everywhere = request.args.get('everywhere')
#     print('hello whats going on')

#     if not everywhere:

#         # get the jti of the access token
#         access_token = get_jwt()
#         access_token_jti = get_jti(access_token)
#         TokenBlocklist.revoke_token(current_user.id, access_token_jti, 'access')

#         # refresh_token_data = get_jti(access_token['refresh_token'])
#         # TokenBlocklist.revoke_token(current_user.id, refresh_token_data, 'refresh')
    
#     else:

#         TokenBlocklist.revoke_all_user_tokens(current_user.id)

#     response = make_response(resolve_redirect(url_for('inter.auth.auth_flow')))
#     unset_jwt_cookies(response)
#     return response

# @auth.route('/test-unset', methods=['GET'])
# def test_unset():
#     response = make_response(resolve_redirect(url_for('inter.auth.auth_flow')))
#     unset_jwt_cookies(response)
#     return response