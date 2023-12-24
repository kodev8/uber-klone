from flask import request
from flask_login import current_user
from flask_babelex import gettext as _, get_locale
from utils.helper import logging, socket_roles_required
from utils.extensions import socketio, redis_client
from utils.mongo import driver_data
from flask_socketio import  join_room, leave_room, disconnect

@socketio.on('connect', namespace='/drivers')
def connect():
    pass
    print('Driver Client connected', request.sid)

@socketio.on('disconnect', namespace='/drivers')
def disconnect():
    pass
    print('Driver Client disconnected', request.sid)


@socketio.on('join', namespace='/drivers')
@socket_roles_required(['driver'])
def join(data):

    error_sweep = {
        'user':repr(current_user),
        'request':request,
        'sid':request.sid,
    }
    try:
        ride_option = data['room']
        if not ride_option:
            raise ValueError('Invalid ride option')
        
        # check if driver has the ride option 
        current_driver_data = driver_data.find_one({'user_id': current_user.id})
        if not current_driver_data or not current_driver_data.get('ride-option') or current_driver_data.get('ride-option') != ride_option:
            raise ValueError('Driver has no ride option or ride option does not match')
        
        #  add the sid to the redis to send notifications to all drivers of this ride option
        locale = request.cookies.get('locale')
        redis_client.sadd(f'ride_option:{ride_option}', f'{request.sid}:{locale}')
        join_room(ride_option)

        print(f'Driver Client joined {ride_option}', request.sid,)
    
    except Exception as e:
        logging.error(f'Error Joining room {e}', exc_info=True, stack_info=True, stacklevel=2, extra=error_sweep)
        return

@socketio.on('leave', namespace='/drivers')
@socket_roles_required(['driver'])
def leave(data):

    error_sweep = {
        'user':repr(current_user),
        'request':request,
        'sid':request.sid,
    }
    
    try:
        ride_option = data['room']
        if not ride_option:
            raise ValueError('Invalid ride option')
        
        #  remove the sid from the redis to send notifications to all drivers of this ride option
        redis_client.srem(f'ride_option:{ride_option}', f'{request.sid}:*')
        print(f'Driver Client left {ride_option}', request.sid)

        leave_room(ride_option)
        disconnect()

    except Exception as e:
        logging.error(f'Error leaving room {e}', exc_info=True, stack_info=True, stacklevel=2, extra=error_sweep)
        return
    

