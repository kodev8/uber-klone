from flask import render_template, url_for, request
from bson import ObjectId
from flask_login import current_user
from auth_bp.emails import send_email_gmail
from datetime import datetime
from utils.mongo import rider_requests, ride_options, payment_methods
from utils.models import User
from utils.helper import resolve_redirect, logging
from pymongo import ReturnDocument
from auth_bp.auth_helper import  enforce_has_request_context

def send_receipt(trip_id, to, is_update=True):  
    """ send receipt of a specific trip to rider or driver"""

    # check if recipient is valid (rider or driver)
    if to not in ['rider', 'driver']:
        raise Exception('Invalid receipt recipient')

    # check if trip exists and user is a member of the trip 
    trip_id_obj = ObjectId(trip_id)

    # check if trip should be updated - made on first receipt send , otherwise just get the trip
    if is_update:
        trip = rider_requests.find_one_and_update({ "$or": [{'driver_id':current_user.id}, {'rider_id':current_user.id}], 'status':'accepted', "_id":trip_id_obj}, 
                                                        {'$set':{
                                                            'status':'completed',
                                                            'ended_at':datetime.now()
                                        
                                                            }
                                                        }
                                                        ,return_document=ReturnDocument.AFTER
                                                        )
    else:
        trip = rider_requests.find_one({ "$or": [{'driver_id':current_user.id}, {'rider_id':current_user.id}], 'status':'completed', "_id":trip_id_obj})
    
    # if no trip found or user is not a member of the trip raise exception
    if not trip:
        raise Exception(f'Trip does not exist or {current_user} is not a member')
    
    # get the ride option name to display on the receipt
    trip['ride_option_name'] = ride_options.find_one({'id':trip['ride_option']})['name']

    # get the driver and rider details to display on the receipt
    driver = User.get_by_id(trip['driver_id'])
    rider = User.get_by_id(trip['rider_id'])

    if not driver:
        raise Exception('Driver not found')
    
    if not rider:
        raise Exception('Rider not found')
    
    # get the payment method details to display on the receipt
    paymethod_data = payment_methods.find_one({'_id': trip['pay_method'], 'user_id':rider.id}, {'_id':0, 'method':1, 'card_number':1, 'email':1})
    if not paymethod_data:
        raise Exception('Payment method not found')
    
    # format the payment method details to display on the receipt
    if paymethod_data['method'] == 'paypal':
        trip['formatted_paymethod'] = f'PayPal: {paymethod_data["email"]}'
    elif paymethod_data['method'] == 'card':
        trip['formatted_paymethod'] = 'Card: xxxx-xxxx-xxxx-' + paymethod_data['card_number'][-4:]
    else:
        trip['formatted_paymethod'] = 'Cash'


    # send the receipt to the rider or driver using the send email gmail function
    if to =='rider':
        rider_email_template = render_template('emails/ride-receipt.html', 
                                            receipt_id=f"r{rider.id}{trip['_id']}", 
                                            ride_cost=trip['rider_price'],
                                            user_name=rider.fname,
                                            other_name=driver.fname,
                                            trip=trip
                                            )
        sent = send_email_gmail(rider.email, rider_email_template, subject='Ride Receipt - KUber')
        if not sent:
            raise Exception('Rider Email not sent')
        
    elif to=='driver':
        driver_email_template = render_template('emails/ride-receipt.html', 
                                            receipt_id=f"d{driver.id}{trip['_id']}", 
                                            ride_cost=trip['driver_price'],
                                            user_name=driver.fname,
                                            other_name=rider.fname,
                                            trip=trip
                                            )
    
        sent = send_email_gmail(driver.email, driver_email_template, subject='Driver Ride Receipt - KUber')
        if not sent:
            raise Exception('Driver Email not sent')
            

@enforce_has_request_context
def verify_paymethod(paymethod):

    """ verify that the paymethod belongs to the user"""
    try:
        paymethodId = ObjectId(paymethod)
        user_paymethod = payment_methods.find_one({'user_id': current_user.id, '_id':paymethodId, 'status':{"$ne":'deleted'}})
        
        if not user_paymethod:
            raise ValueError('Unable to find pay method')
        
        return  paymethodId, user_paymethod
    except Exception as e:
        logging.error(f"ERROR @ {request.endpoint}: {e}", exc_info=True, stack_info=True, stacklevel=3, extra={'request':request})
        return None, None
    
def sort_paymethods(paymethod):
    """ sort the payment methods by method and date to be used as key in the sorted function"""
    # paypal is the first, card is the second, others are the last, then sort by date
    
    method_order = {"paypal": 1, "card": 2}  
    return method_order.get(paymethod["method"], 3), paymethod['date']