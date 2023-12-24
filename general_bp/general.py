from flask import Blueprint, render_template, request
from flask_login import current_user
from flask_babelex import gettext as _
from utils.codes import CODES
from utils.helper import htmx_request, logging
from utils.codes import CODES
from utils.config import DRIVER_STATE
from utils.notifications import notify_accept_error_modal
# from flask_jwt_extended import create_access_token, get_jwt_identity, set_access_cookies, get_jwt, current_user as jwt_current_user, verify_jwt_in_request

general = Blueprint('general', __name__, template_folder='general_templates')
    
@general.route('/', methods=['GET'])
def index():

    # check if user is admin to display base page for admins
    is_admin = False
    if current_user.is_authenticated and current_user.has_role('admin'):
        is_admin = True

    if not is_admin:
        tab = request.args.get('tab', 'dod')
    else:
        tab = request.args.get('tab', 'dashboard')

    return render_template('index.html', tab=tab, DRIVER_STATE=DRIVER_STATE, is_admin=is_admin)


@general.route('/nav-drawer', methods=['GET'])
@htmx_request
def nav_drawer():
    
    # used to render drop down content from the navigation bar on the index page
    
    try:
        content = request.args.get('content')
        opened = request.args.get('opened', False)
        opened = opened == 'true'

        # allowed content
        if content not in ('login', 'sign-up', 'select-language', 'logged-in'):
            return '', CODES.NO_CONTENT
        
        # print(opened, jwt_current_user)
        return render_template('general_htmx/nav-drawer.html', content=content, opened=opened, DRIVER_STATE=DRIVER_STATE)
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=2, extra={'request':request})
        return notify_accept_error_modal('Something went wrong, please try again later', 'Server Erorr'), CODES.INTERNAL_SERVER_ERROR



