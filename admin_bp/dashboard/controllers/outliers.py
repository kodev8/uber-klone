import ast

from admin_bp.dashboard.core.logger import log
from admin_bp.dashboard.core.colors import get_color
from admin_bp.dashboard.core.timezone import to_local_datetime
from admin_bp.dashboard.core.utils import simplify
from admin_bp.dashboard.database import row2dict
from admin_bp.dashboard.database.outlier import get_outliers_cpus, get_outliers_sorted


def get_outlier_graph(session, endpoint_id):
    """
    :param session: session for the database
    :param endpoint_id: id of the endpoint
    :return: a list with data about each CPU performance
    """
    all_cpus = get_outliers_cpus(session, endpoint_id)
    cpu_data = [ast.literal_eval(cpu) for cpu in all_cpus]

    return [
        {'name': 'CPU core %d' % idx, 'values': simplify(data, 50), 'color': get_color(idx)}
        for idx, data in enumerate(zip(*cpu_data))
    ]


def get_outlier_table(session, endpoint_id, offset, per_page):
    """
    :param session: session for the database
    :param endpoint_id: id of the endpoint
    :param offset: number of items to be skipped
    :param per_page: maximum number of items to be returned
    :return: a list of length at most 'per_page' with data about each outlier
    """
    table = get_outliers_sorted(session, endpoint_id, offset, per_page)
    for idx, row in enumerate(table):
        row.request.time_requested = to_local_datetime(row.request.time_requested)
        try:
            row.request_url = row.request_url.decode('utf-8')
        except Exception as e:
            log(e)
        dict_request = row2dict(row.request)
        table[idx] = row2dict(row)
        table[idx]['request'] = dict_request
    return table
