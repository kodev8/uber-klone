from flask import jsonify

from admin_bp.dashboard.controllers.outliers import get_outlier_graph, get_outlier_table
from admin_bp.dashboard.database.count import count_outliers

from admin_bp.dashboard.database import session_scope

from admin_bp.dashboard.core.auth import secure
from admin_bp.dashboard.core.telemetry import post_to_back_if_telemetry_enabled
from admin_bp.dashboard import blueprint


@blueprint.route('/api/num_outliers/<endpoint_id>')
# @secure
def num_outliers(endpoint_id):
    post_to_back_if_telemetry_enabled(**{'name': f'num_outliers/{endpoint_id}'})
    with session_scope() as session:
        return jsonify(count_outliers(session, endpoint_id))


@blueprint.route('/api/outlier_graph/<endpoint_id>')
# @secure
def outlier_graph(endpoint_id):
    post_to_back_if_telemetry_enabled(**{'name': f'outlier_graph/{endpoint_id}'})
    with session_scope() as session:
        return jsonify(get_outlier_graph(session, endpoint_id))


@blueprint.route('/api/outlier_table/<endpoint_id>/<offset>/<per_page>')
# @secure
def outlier_table(endpoint_id, offset, per_page):
    post_to_back_if_telemetry_enabled(**{'name': f'outlier_table/{endpoint_id}'})
    with session_scope() as session:
        return jsonify(get_outlier_table(session, endpoint_id, offset, per_page))
