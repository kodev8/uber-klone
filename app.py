# FLASK
from flask import Flask, render_template, send_from_directory, request, session, url_for, g, flash, abort
from flask_login import login_required
from flask_babelex import gettext as _, get_locale
# from flask_jwt_extended import create_access_token, get_jwt_identity, set_access_cookies, get_jwt, current_user as jwt_current_user, verify_jwt_in_request, get_current_user
from babel import numbers, dates

# UTILS
from utils.helper import  htmx_request, resolve_redirect, get_currency_code, convert_currency
from utils.config import Config, FLASK_TESTING
from utils.models import User, Role
from utils.extensions import db, jwt, scheduler, redis_client, login_manager, socketio, debug_toolbar, babel
from utils.codes import CODES
from utils.notifications import notify
import utils.error_handlers as error_handlers
from utils.setup import setup_app

# BLUEPRINTS
from auth_bp.auth import auth
from general_bp.general import general
from riders_bp.riders import riders
from drivers_bp.drivers import drivers
from chat_bp.chat import chat
from locations_bp.locations import locations
from account_bp.account import account
from admin_bp.admin import admin
import admin_bp.dashboard as dashboard
from inter import inter_bp

def create_app():
# APP CONFIG
    app = Flask(__name__, static_folder='./static')
    app.config.from_object(Config)
    # app.testing=FLASK_TESTING

    # initialize extensions
    db.init_app(app)
    scheduler.init_app(app)
    scheduler.start()
    redis_client.init_app(app)
    babel.init_app(app)

    if app.testing:
        debug_toolbar.init_app(app)

    login_manager.init_app(app)
    @login_manager.user_loader
    def user_loader(user_id):
        return User.get_by_id(user_id)
    login_manager.login_view = '/auth'
    login_manager.login_message = ''

    socketio.init_app(app, cors_allowed_origins="*", message_queue=app.config['REDIS_URL'])


    #  register blueprints
    inter_bp.register_blueprint(auth)
    inter_bp.register_blueprint(general)
    inter_bp.register_blueprint(riders)
    inter_bp.register_blueprint(drivers)
    inter_bp.register_blueprint(account)
    inter_bp.register_blueprint(chat)
    dashboard.config.init_from(envvar='FLASK_MONITORING_DASHBOARD_CONFIG')
    dashboard.bind(app, custom_bp=admin, schedule=False, include_dashboard=True) # register dashboard blueprint before admin blueprint
    inter_bp.register_blueprint(admin)
    app.register_blueprint(locations)
    app.register_blueprint(inter_bp)


    # register error handlers
    error_handlers.init_code_error_handlers(app)

    @babel.localeselector
    def get_app_locale():
        lang = g.get('lang', app.config['BABEL_DEFAULT_LOCALE'])
        return lang

    @app.template_filter('format_currency')
    def format_currency(value):
        locale_str = str(get_locale())
        # print(locale_str,'LOCALE', type(locale_str))
        currency_code = get_currency_code(locale_str)
        converted_value = convert_currency(value, 'USD', currency_code)
        return numbers.format_currency(converted_value, currency_code, locale=locale_str)

    @app.template_filter('format_datetime')
    def format_datetime_filter(date, format='medium'):
        locale_str = get_locale()
        date = dates.format_datetime(date, format=format, locale=locale_str)
        return date

    @app.route('/')
    @app.route('/<string:base>')
    @app.route('/<path:path>')
    def index(path=None, base=None):

        adapter = app.url_map.bind_to_environ(request.environ)

        # check if route is ok using the current request path with the current language
        default_lang = app.config['BABEL_DEFAULT_LOCALE']
        lang = g.get('lang', default_lang)

        # route1 check
        if path or base:
            route1 = '/' + lang + request.path.rstrip('/')
        else:
            route1 = '/' + lang + '/'
        
        # route2 check
        # check if route is ok if replace the first part of the route with the current language
        route2 = None
        if path and len(path.split('/')) > 1:
            route2 = '/' + lang + '/' + '/'.join(path.split('/')[1:])
        
        try:
            
            # check if either route or route2 is valid otherwise abort
            endpoint, args = adapter.match(route1, method='GET')
            if endpoint and endpoint != request.endpoint:
                return resolve_redirect(url_for(endpoint, **args, **request.args))
            if route2:
                endpoint, args = adapter.match(route2, method='GET')
                if endpoint and endpoint != request.endpoint:
                    return resolve_redirect(url_for(endpoint, **args, **request.args))
            raise Exception('No valid endpoint found')
        except Exception as e:
            return abort(CODES.NOT_FOUND)

    @app.route('/uploads/<path:filename>')
    @login_required
    def profile_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/close-modal', methods=['GET'])
    @htmx_request
    def close_modal(): 
        return render_template('htmx/modals/closed-modal.html')

    @app.post('/set-lang')
    def set_lang():
        # handled by babel
        lang = request.form.get('lang')
        if lang and lang in app.config['LANGUAGES']:
            g.lang = lang
        else:
            lang = 'en'
        return resolve_redirect(url_for('inter.general.index'))

    @app.route('/dev-not-imp', methods=['GET','POST'])
    @htmx_request
    def not_implemented():
        return notify(_("This feature is not yet implemented") ,"info", code=CODES.NOT_IMPLEMENTED)
        
    @app.route('/clear')
    def clear():
        return ""
    
    with app.app_context():
        db.create_all()
        Role._init_roles()
    
    return app

if __name__ == '__main__':
#     # url = 'kuber.test:5000'
#     # app.config['SERVER_NAME'] = url

    app = create_app()

    # if app.config['FLASK_ENV'] == 'production':
    socketio.run(app)

#     if app.config['FLASK_ENV'] == 'development':
#         socketio.run(app, debug=True, port=5000)

#         with app.app_context():
#             db.session.close()

#     elif app.config['FLASK_ENV'] == 'setup':
#         setup_app()


# https://github.com/vimalloc/flask-jwt-extended/issues/478 -- make current user available in jwt context in templates
# jwt.init_app(app)
# def jwt_current_user_context_processor():
#     return {"jwt_current_user": get_current_user()}
# app.context_processor(jwt_current_user_context_processor)

    # @login_manager.user_loader
# def user_loader(admin_id):
#     return Admin.get_by_id(admin_id)

# managing session
# @app.before_request
# def manage_session():
#     verify_jwt_in_request(optional=True)

# @app.after_request
# def manage_auth(response):
#     print("Response Headers:")
#     for key, value in response.headers.items():
#         print(f"{key}: {value}")
    
#     return response

# def manage_auth():  
#     if current_user.is_authenticated and request.method == "GET" and request.endpoint in ('register', 'login', 'auth_flow'):
#         return resolve_redirect(url_for('general.index'))
    
#     elif current_user.is_anonymous and request.endpoint in ('register', 'login') and not session.get('email'):
#         return resolve_redirect('/auth')
