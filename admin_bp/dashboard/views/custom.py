import datetime

from flask.json import jsonify

from admin_bp.dashboard import blueprint
# from admin_bp.dashboard.core.auth import secure
from admin_bp.dashboard.core.custom_graph import get_custom_graphs
from admin_bp.dashboard.core.telemetry import post_to_back_if_telemetry_enabled
from admin_bp.dashboard.database import row2dict, session_scope
from admin_bp.dashboard.database.custom_graph import get_graph_data


@blueprint.route('/api/custom_graphs')
# @secure
def custom_graphs():
    post_to_back_if_telemetry_enabled(**{'name': 'custom_graphs'})
    graphs = get_custom_graphs()
    if not graphs:
        return jsonify([])
    return jsonify([row2dict(row) for row in graphs if row is not None])


@blueprint.route('/api/custom_graph/<graph_id>/<start_date>/<end_date>')
# @secure
def custom_graph(graph_id, start_date, end_date):
    post_to_back_if_telemetry_enabled(**{'name': f'custom_graph{graph_id}'})
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    with session_scope() as session:
        return jsonify(get_graph_data(session, graph_id, start_date, end_date))
