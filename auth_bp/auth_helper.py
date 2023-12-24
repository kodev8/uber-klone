from flask import render_template, request, session, make_response, has_request_context
from utils.codes import CODES
from auth_bp.forms import CodeForm
from utils.codes import CODES
from random import random
from uuid import uuid4
from datetime import timedelta, datetime
import json
from functools import wraps
from utils.extensions import scheduler, redis_client
from auth_bp.emails import send_email_gmail
from utils.notifications import notify_accept_error_modal

# from flask_jwt_extended import (create_access_token, 
#                                 get_jwt_identity, 
#                                 jwt_required, 
#                                 set_access_cookies, 
#                                 set_refresh_cookies, 
#                                 create_refresh_token,
#                                 get_jti,
#                                 get_jwt, 
#                                 unset_jwt_cookies,
#                                 current_user)

# def login_user(response, user):
#     assert type(response) == Response
#     assert type(user) == User

#     # create jwt token
#     refresh_token = create_refresh_token(identity=user.email)
#     # embed refresh token in access token used for logout all in one request
#     access_token = create_access_token(identity=user.email, fresh=True, additional_claims={'refresh_token': refresh_token})
    
#     # set jwt token in cookies
#     set_access_cookies(response, access_token)
#     set_refresh_cookies(response, refresh_token)

#     # set jwt token in db for revoking
#     TokenBlocklist.add_token(TokenBlocklist(jti=get_jti(access_token), type='access', user_id=user.id))
#     TokenBlocklist.add_token(TokenBlocklist(jti=get_jti(refresh_token), type='refresh', user_id=user.id))

#     return response
def gen_code():
    """ generates 4 digit OTP"""
    return str(int(random()*10000)).zfill(4)

def enforce_has_request_context(func):
    """ checks if the function is called within a request context"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not has_request_context():
            raise RuntimeError("This method can only be called within a request context")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def auth_session_id_required(func):
    """ checks if auth_session_id is in request header and  session and if it is valid"""
    @wraps(func)
    def wrapper(*args, **kwargs):

        auth_session_id = request.headers.get('X-Auth-Session-Id')  
        session_data = session.get(auth_session_id)
        if not auth_session_id or not session_data:
            return notify_accept_error_modal("failed to get from database: Expired: inAuthSession expired",code=CODES.UNAUTHORIZED)
           
        
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__

    return wrapper

@enforce_has_request_context
def get_auth_redis_data(key="all"):

    """ gets the auth data from redis, either all or a specific key,
    only to be called from within  a route decorated with auth_session_id_required"""
    auth_session_id = request.headers.get('X-Auth-Session-Id')  

    if key == "all":
        # print(redis_client.hgetall(auth_session_id))
        return redis_client.hgetall(auth_session_id)
    else:
        return redis_client.hget(auth_session_id, key)

def remove_auth_session_data_code(auth_session_id):
    redis_client.hdel(auth_session_id, 'code')

def send_verification_code_email(email,
                                 start_url, 
                                 action,
                                 template_message, 
                                 template_header, 
                                 is_user,
                                 user_name="",
                                 is_driver=False,
                                 next=None
                                 ):
    
    """ sends the verification code to the user via email"""

    # generate the OTP
    code  = gen_code()

    # use smtp to send mail and check if it was sent, else notify the user that is was not sent
    send_email_att = send_email_gmail(email, content=render_template('emails/verification-code.html',code=code, template_message=template_message, template_header=template_header), 
                                subject="Your Uber Verification Code",
                                name=user_name)
    
    if not send_email_att:
        # print("Failed by auth_flow: send_email_att ")
        err_resp = make_response(render_template('htmx/notif.html', message="Unable to send verification code", type="error"))
        err_resp.status_code = CODES.UNAUTHORIZED
        err_resp.headers['HX-Retarget'] = '#messages'
        return err_resp

    # create a session id for the auth to distinguish log in with in the same session similar to uber 
    inAuthSessionId = str(uuid4())
    form=CodeForm()

    print(email, code)

    # set the auth id in the session
    session[inAuthSessionId] = {
        'email': email,
    }

    redis_data = {
        'email': email,
        'code': code,
        'is_driver': int(is_driver),
    }

    if next:
        redis_data['next'] = next

    redis_client.hset(inAuthSessionId, mapping=redis_data)

    redis_client.expire(inAuthSessionId, timedelta(minutes=15))

    scheduler.add_job(func=remove_auth_session_data_code, args=[inAuthSessionId], id=f"remove_auth_session_id_{inAuthSessionId}_code", trigger='date', run_date=datetime.now() + timedelta(minutes=15))
    response = make_response(render_template('flow.html', form=form, step=2, email=email,is_user=is_user,action=action,start_url=start_url ))

    # triggers setInAuthSessionId via js for all subsequent requests during auth flow
    response.headers['X-Allow-Trigger'] = True
    response.headers["HX-Trigger-After-Swap"] = json.dumps(
        {
            "setInAuthSessionId":{
               'inAuthSessionId': inAuthSessionId
            }, 
            "linkInputsToNext": None
        }
    )

    return response

def validate_email_code(action=None):
    """ validates the OTP sent via email"""
    
    form = CodeForm()

    # get the code from the form and the redis data
    code = get_auth_redis_data('code')
    email = get_auth_redis_data('email')
    form_data = ''.join((str(field.data) for field in form if field.id != 'csrf_token'))

    print('email', email, code, form_data) # display code if not sending email

    if not form.validate_on_submit() or form_data != code:
        resp = make_response(render_template('flow.html', form=CodeForm(formdata=None), step=2, code_error="Incorrect code! Please try again.", action=action))
        resp.status_code = CODES.UNAUTHORIZED
        resp.headers["HX-Reselect"] = "#auth-flow-form"
        return False, resp
    
    return True, email