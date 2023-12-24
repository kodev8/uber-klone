from flask import render_template, make_response
from utils.codes import CODES

def notify_accept_error_modal(message, header="Bad Request", code=CODES.BAD_REQUEST):
    """Notify the user of an error in the request via modal via htmx"""
    resp = make_response(render_template('htmx/modals/notify-accept.html', message=message, header=header))
    resp.headers['HX-Retarget'] = '#modal-bg'
    resp.headers['Hx-Reswap'] = 'outerHTML'
    resp.headers['Hx-Reselect'] = '#modal-bg'
    resp.status_code = code
    return resp

def notify(message, type, link=None, code=CODES.OK, headers=None):
    """Notify the user of an error in the request via top dropdown notification via htmx"""
    resp = make_response(render_template('htmx/notif.html', message=message, type=type, link=link))
    resp.headers['HX-Retarget'] = '#messages'
    resp.headers['HX-Reselect'] = '.notif'
    resp.headers['HX-Reswap'] = 'innerHTML'
    if headers:
        for key, value in headers.items():
            resp.headers[key] = value
    resp.status_code = code
    return resp
