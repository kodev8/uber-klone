import numpy as np
from flask import url_for
from werkzeug.routing import BuildError

from admin_bp.dashboard import config
from admin_bp.dashboard.core.colors import get_color
from admin_bp.dashboard.core.rules import get_rules
from admin_bp.dashboard.core.timezone import to_local_datetime
from admin_bp.dashboard.database.count import count_requests, count_total_requests
from admin_bp.dashboard.database.endpoint import get_endpoint_by_id
from admin_bp.dashboard.database.request import (
    get_date_of_first_request,
    get_date_of_first_request_version,
)


def get_endpoint_details(session, endpoint_id):
    """
    Returns details about an endpoint.
    :param session: session for the database
    :param endpoint_id: id of the endpoint
    :return dictionary
    """
    endpoint = get_endpoint_by_id(session, endpoint_id)
    endpoint.time_added = to_local_datetime(endpoint.time_added)
    flask_rule = get_rules(endpoint.name)
    methods = [list(rule.methods) for rule in flask_rule]
    methods = sum(methods, [])  # flatten list
    return {
        'id': endpoint_id,
        'color': get_color(endpoint.name),
        'methods': list(dict.fromkeys(methods)),
        'endpoint': endpoint.name,
        'rules': [r.rule for r in get_rules(endpoint.name)],
        'monitor-level': endpoint.monitor_level,
        'url': get_url(endpoint.name),
        'total_hits': count_requests(session, endpoint.id),
    }


def get_details(session):
    """
    Returns details about the deployment.
    :param session: session for the database
    :return dictionary
    """
    import json
    from admin_bp.dashboard import loc

    with open(loc() + 'constants.json', 'r') as f:
        constants = json.load(f)

    return {
        'link': config.link,
        'dashboard-version': constants['version'],
        'config-version': config.version,
        'first-request': get_date_of_first_request(session),
        'first-request-version': get_date_of_first_request_version(session, config.version),
        'total-requests': count_total_requests(session),
    }


def get_url(end):
    """
    Returns the URL if possible.
    URL's that require additional arguments, like /static/<file> cannot be retrieved.
    :param end: the endpoint for the url.
    :return: the url_for(end) or None,
    """
    try:
        return url_for(end)
    except BuildError:
        return None


def simplify(values, n=5):
    """
    Simplify a list of values. It returns a list that is representative for the input
    :param values: list of values
    :param n: length of the returned list
    :return: list with n values: min, q1, median, q3, max
    """
    if len(values) <= n:
        return values
    return [np.percentile(values, i * 100 // (n - 1)) for i in range(n)]
