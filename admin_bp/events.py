from flask import request
from utils.extensions import socketio, redis_client
from utils.config import Config
from utils.helper import socket_roles_required

@socketio.on('connect', namespace='/admin')
@socket_roles_required(['admin'])
def connect():
    locale = request.cookies.get('locale', 'en')
    # print('Admin Client connected', locale)
    redis_client.sadd('admins', f"{request.sid}:{locale}")

@socketio.on('disconnect', namespace='/admin')
@socket_roles_required(['admin'])
def disconnect():
    # print('Admin Client disconnected')
    redis_client.srem('admins', f"{request.sid}:*")


# @socketio.on('submit-driver-application')
# def submit_driver_application(data):
#     print(data, 'received')
#     socketio.emit('driver-application-response', data, namespace='/admin')

