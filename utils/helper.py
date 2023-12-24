from flask import url_for, Response, request, redirect, flash, abort
from flask_login import current_user, login_required
import locale
from currency_converter import CurrencyConverter
from utils.codes import CODES
import logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] : %(message)s')

# Exclude logs from the "werkzeug" logger
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.propagate = False

scheduler_logger = logging.getLogger('apscheduler.executors.default')
scheduler_logger.setLevel(logging.ERROR)
scheduler_logger.propagate = False



def htmx_redirect(endpoint, code=200):
    """ Redirects to endpoint with htmx headers 
        :param endpoint: endpoint to redirect to
        :param code: status code to be returned
    """
    response = Response()
    response.headers["HX-Redirect"] = endpoint
    response.status_code = code

    return response

def resolve_redirect(endpoint, message=None):
    """ Resolves redirect based on request type
        :param endpoint: endpoint to redirect to
        :param message: message to be flashed
    """
    redirect_method = htmx_redirect if 'hx-request' in request.headers else redirect
    if message:
        flash(message.get('text', 'Notification'), message.get('type' ,'success'))
    return redirect_method(endpoint, code=302)

def htmx_request(view_func): 
    """ Decorator to check if request is htmx request 
        :param view_func: view function to be decorated
    """
    def wrapper_func(*args, **kwargs): 
        if 'hx-request' in request.headers: 
            return view_func(*args, **kwargs) 
        else: 
            return {}, CODES.NO_CONTENT
    # renames wrapper for unique name to avoid: AssertionError: View function mapping is overwriting an existing endpoint function: wrapper_func
    wrapper_func.__name__ = view_func.__name__
    return wrapper_func

# extended to allow for many roles
def roles_required(route_required_roles: list = [], fallback_endpoint=None):
    """ Decorator to check if user has required roles to access a route
        :param route_required_roles: list of roles required to access route as strings
        :param fallback_endpoint: endpoint to redirect to if user does not have required roles
    """
    def wrapper(view):
        @login_required
        def role_check(*args, **kwargs):
            has_role = False
            for role in route_required_roles:
                if current_user.has_role(role):
                    has_role = True
                    break
            if not has_role:
                if fallback_endpoint:
                    # print(fallback_endpoint, 'has been called')
                    return resolve_redirect(url_for(fallback_endpoint))
                return abort(CODES.FORBIDDEN)
            return view(*args, **kwargs)
        role_check.__name__ = view.__name__
        return role_check
    return wrapper        

def socket_roles_required(route_required_roles: list = []):
    """ Decorator to check if user has required roles to access a socketio route
        :param route_required_roles: list of roles required to access route as stringds

    """
    def wrapper(view):
        def role_check(*args, **kwargs):
            if not current_user.is_authenticated:
                return 
            has_role = False
            for role in route_required_roles:
                if current_user.has_role(role):
                    has_role = True
                    break
            if not has_role:
                return
            return view(*args, **kwargs)
        role_check.__name__ = view.__name__
        return role_check
    return wrapper

def get_currency_code(locale_str):
    """ Gets the currency code for the specified locale
        :param locale_str: locale string to get currency code for
    """
    # Set the locale default or default to None
    try:
        locale.setlocale(locale.LC_MONETARY, locale_str)
    except locale.Error:
        return None

    # Get the formatting parameters for the current locale
    formatting_params = locale.localeconv()

    # Extract the currency code
    currency_code = formatting_params['int_curr_symbol']

    return currency_code

c = CurrencyConverter()
def convert_currency(value, from_currency, to_currency):
    """ Converts currency from one currency to another
        :param value: value to be converted
        :param from_currency: currency to be converted from
        :param to_currency: currency to be converted to
    """
    try:
        return c.convert(value, from_currency, to_currency)
    except Exception:
        # return original value if conversion fails
        return value
    