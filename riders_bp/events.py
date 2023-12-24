from flask import request
from flask_login import current_user
from utils.helper import logging, socket_roles_required
from utils.extensions import socketio
from flask_socketio import join_room


@socketio.on('connect', namespace='/riders')
def connect():
    pass
    # print('Rider Client connected')

@socketio.on('disconnect', namespace='/riders')
def disconnect():
    pass
    # print('Rider Client disconnected')

@socketio.on('join', namespace='/riders')
@socket_roles_required(['rider'])
def join(data):
    error_sweep = {
        'user':repr(current_user),
        'request':request,
        'sid':request.sid,
    }
    try:
        ride_request_id = data['room']
        # print('rider join', ride_request_id)
        if not ride_request_id:
            raise ValueError('Invalid ride option')
        
        join_room(ride_request_id)
        # print(f'Rider Client joined {ride_request_id}')
    except Exception as e:
        logging.error(f'Error Joining room {e}', exc_info=True, stack_info=True, stacklevel=2, extra=error_sweep)
        return

