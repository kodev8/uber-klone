from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_jwt_extended import JWTManager
from flask_redis import FlaskRedis
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_debugtoolbar import DebugToolbarExtension
from flask_babelex import Babel



# debug toolbar for debugging
debug_toolbar = DebugToolbarExtension()

# sqlalchemy for database --more persistent data
class Base(DeclarativeBase):
    pass 

db = SQLAlchemy(model_class=Base)

# apscheduler for scheduling jobs
scheduler = APScheduler()

# jwt based log in for users
jwt = JWTManager()

# redis for storing tokens and otps
redis_client = FlaskRedis(decode_responses=True)

# session based log in
login_manager = LoginManager()

# flask socket io for chat
socketio = SocketIO()

# flask babel for translations
babel = Babel()
