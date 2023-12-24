from utils.extensions import socketio, redis_client
from flask import render_template, request, url_for
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room, disconnect, rooms
from flask_babelex import gettext as _, get_locale
from utils.mongo import rider_requests, driver_data
from utils.helper import socket_roles_required, logging
from bson import ObjectId
from account_bp.account_helper import send_receipt
from datetime import datetime
import json

# connext to chat room
@socketio.on('connect', namespace='/chat')
@socket_roles_required(['rider', 'driver'])
def connect():
    # print('chat connected', rooms())
    emit('connected')

# disconnect from chat room
@socketio.on('disconnect', namespace='/chat')
@socket_roles_required(['rider', 'driver'])
def disconnect():
    # print('chat disconnected')
    emit('disconnected')

# join chat room
@socketio.on('join', namespace='/chat')
@socket_roles_required(['rider', 'driver'])
def join(data):
    # print('joined')
    try:
        room = data['room']
        roomId = ObjectId(room)
        check_room = rider_requests.find_one({ "$or": [{'driver_id':current_user.id}, {'rider_id':current_user.id}], 'status':'accepted', "_id":roomId},)
        if not check_room:
            raise Exception(f'Room does not exist or {current_user} is not a member')
        
        # add user to redis room
        redis_client.sadd(f'room:{current_user.id}:{roomId}', request.sid)

        join_room(room)
        emit('joined', {'data': 'Joined'})

    except Exception as e:
        logging.error(f'Error joining driver room {e}')
        disconnect()

# leave chat room
@socketio.on('leave', namespace='/chat')
@socket_roles_required(['rider', 'driver'])
def leave(data):
    try:
        room = data['room']

        send_receipt(room, 'rider')
        send_receipt(room, 'driver', is_update=False)

        # get trip driver price and increment driver bank balance
        roomId = ObjectId(room)
        trip = rider_requests.find_one({'_id':roomId})
        driver = trip['driver_id']
        base, decimal = trip['driver_price'].split('.')
        if len(decimal) > 2:
            decimal = decimal[:2] # dont round up
        driver_price = float(f'{base}.{decimal}')
        driver_price = float(trip['driver_price'])
        driver_data.update_one({'user_id':driver}, {'$inc':{'bank.balance':driver_price}})

        # emit ride complete event to rider and driver
        emit('leave', {'template': render_template('ride_complete.html'), 'redirect_url':url_for('inter.account.trip_details', ride_id=room)}, room=room, include_self=True)
        
        # remove room and messages from redis
        redis_client.delete(f'room:*:{room}')
        redis_client.delete(f'messages:{room}')

        logging.info(f'Ride completed: {room}')
        
        # remove user from room
        leave_room(room)
        disconnect() 

    except Exception as e:
        logging.error(f'Error leaving room {e}')
        return
    


# send message to chat room
@socketio.on('message', namespace='/chat')
@socket_roles_required(['rider', 'driver'])
def message(data):

    error_sweep = {
        'user':repr(current_user),
        'request':request,
        'sid':request.sid,
    }
    try:
        # backend check for empty message
        if not data['msg']:
            raise ValueError('Message is empty')
        error_sweep['msg'] = data['msg']
        
        if not data['room']:
            raise ValueError('Room is empty')
        error_sweep['room'] = data['room']
        
        # backend check for room membership
        room = data['room']
        roomId = ObjectId(room)
        check_room = rider_requests.find_one({ "$or": [{'driver_id':current_user.id}, {'rider_id':current_user.id}], 'status':'accepted', "_id":roomId},)
        
        if not check_room:
            raise ValueError(f'Room does not exist or {current_user} is not a member')

        # get other member sids (all other clients in the room that are not the sender)
        if current_user.id == check_room['driver_id']:
            other_sids = redis_client.smembers(f'room:{check_room["rider_id"]}:{roomId}')
        else:
            other_sids = redis_client.smembers(f'room:{check_room["driver_id"]}:{roomId}')

        # store messages in redis
        message_data = {
            'sender':current_user.id,
            'message':data['msg'],
            'created_at':datetime.now().timestamp()
        }

        #  add message to redis sorted set, use timestamp as score for sorting
        redis_client.zadd(f'messages:{roomId}', {json.dumps(message_data): int(message_data['created_at'])})

        # emit send message to chat room to rider and driver
        emit('send message', {'msg': render_template('send-chat.html', is_sender=True, user=current_user, text=data['msg'])}, room=data['room'], include_self=True, skip_sid=list(other_sids)) # skip send messgae to all other user sids and only include sender sids
        emit('receive message', {'msg': render_template('send-chat.html', is_sender=False, user=current_user, text=data['msg'])}, room=data['room'], include_self=False) # receive message to other sids only

    except ValueError as ve:
        logging.error(f'Error sending message {ve}', exc_info=True, stack_info=True, stacklevel=2, extra=error_sweep)
        return
        
    except Exception as e:
        logging.error(f'Error sending message {ve}', exc_info=True, stack_info=True, stacklevel=2, extra=error_sweep)
        return