import os

from flask import Blueprint

from admin_bp.dashboard.core.config import Config, TelemetryConfig
from admin_bp.dashboard.core.logger import log


def loc():
    """Get the current location of the project."""
    return os.path.abspath(os.path.dirname(__file__)) + '/'


config = Config()
telemetry_config = TelemetryConfig()
blueprint = Blueprint('dashboard', __name__, template_folder=loc() + 'templates')


def bind(app, custom_bp=None, schedule=True, include_dashboard=True):
    """Binding the app to this object should happen before importing the routing-
    methods below. Thus, the importing statement is part of this function.

    :param app: the app for which the performance has to be tracked
    :param schedule: flag telling if the background scheduler should be started
    :param include_dashboard: flag telling if the views should be added or not.
    """
    config.app = app
    # Provide a secret-key for using WTF-forms
    if not app.secret_key:
        log('WARNING: You should provide a security key.')
        app.secret_key = 'my-secret-key'

    # Add all route-functions to the blueprint
    if include_dashboard:
        from admin_bp.dashboard.views import (
            deployment,
            custom,
            endpoint,
            outlier,
            request,
            profiler,
            version,
            auth,
            reporting,
            telemetry
        )
        import admin_bp.dashboard.views

    # Add wrappers to the endpoints that have to be monitored
    from admin_bp.dashboard.core.measurement import init_measurement
    from admin_bp.dashboard.core.cache import init_cache
    from admin_bp.dashboard.core import custom_graph

    blueprint.record_once(lambda _state: init_measurement())
    blueprint.record_once(lambda _state: init_cache())
    if schedule:
        custom_graph.init(app)

    # register the blueprint to the app
    if not custom_bp:
        custom_bp = app
        blueprint.name = config.blueprint_name


    custom_bp.register_blueprint(blueprint, url_prefix='/' + config.link)
    

    # flush cache to db before shutdown
    import atexit
    from admin_bp.dashboard.core.cache import flush_cache

    atexit.register(flush_cache)

    if not include_dashboard:
        @app.teardown_request
        def teardown(_):
            flush_cache()


def add_graph(title, func, trigger="interval", **schedule):
    """Add a custom graph to the dashboard. You must specify the following arguments:

    :param title: title of the graph (must be unique)
    :param schedule: dict containing values for weeks, days, hours, minutes, seconds
    :param func: function reference without arguments
    :param trigger: str|apscheduler.triggers.base.BaseTrigger trigger: trigger that determines when
            ``func`` is called
    """
    from admin_bp.dashboard.core import custom_graph

    graph_id = custom_graph.register_graph(title)
    custom_graph.add_background_job(func, graph_id, trigger, **schedule)
