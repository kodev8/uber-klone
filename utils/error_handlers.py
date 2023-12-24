from flask import render_template, make_response, request, url_for
from flask_babelex import gettext as _
from utils.codes import CODES


def init_code_error_handlers(app):

    @app.errorhandler(CODES.NOT_FOUND)
    def abort_not_found(e):
        resp = make_response(render_template('codes/err_code.html', code=str(CODES.NOT_FOUND), message=_("Page Not Found!")))
        if 'hx-request' in request.headers:
            resp.headers['HX-Retarget'] = 'body'
        return resp

    @app.errorhandler(CODES.UNAUTHORIZED)
    def abort_unauthorize(e):
        resp = make_response(render_template('codes/err_code.html', 
                                code=str(CODES.UNAUTHORIZED), 
                                message=_("You are not authorized to view the page."), sub_message=f'{_("You should be redirected in a few seconds")}... {_("if not click here")}.'),
                                {"Refresh": f"3; url={url_for('inter.general.index')}"}
        )
        if 'hx-request' in request.headers:
            resp.headers['HX-Retarget'] = 'body'

        return resp

    @app.errorhandler(CODES.FORBIDDEN)
    def abort_forbidden(e):
        resp = make_response(render_template('codes/err_code.html', 
                                code=str(CODES.FORBIDDEN), 
                                message=_("You do not have permission to view this page!"), sub_message=f'{_("You should be redirected in a few seconds")}... {_("if not click here")}.'),
                                {"Refresh": f"3; url={url_for('inter.general.index')}"}
        )
        if 'hx-request' in request.headers:
            resp.headers['HX-Retarget'] = 'body'
        return resp

    @app.errorhandler(CODES.NOT_ALLOWED)
    def abort_method_not_allowed(e):
        resp = make_response(render_template('codes/err_code.html', 
                                code=str(CODES.NOT_ALLOWED), 
                                message=_("Method Not Allowed!"), sub_message=f'{_("You should be redirected in a few seconds")}... {_("if not click here")}.'),
                                {"Refresh": f"3; url={url_for('inter.general.index')}"}
        )
        if 'hx-request' in request.headers:
            resp.headers['HX-Retarget'] = 'body'
        return resp

    @app.errorhandler(CODES.INTERNAL_SERVER_ERROR)
    def abort_method_not_allowed(e):
        
        resp = make_response(render_template('codes/err_code.html', 
                                code=str(CODES.INTERNAL_SERVER_ERROR), 
                                message=_("Server Error has occured!"), sub_message=f'{_("You should be redirected in a few seconds")}... {_("if not click here")}.'),
                                {"Refresh": f"3; url={url_for('inter.general.index')}"}
        )
        if 'hx-request' in request.headers:
            resp.headers['HX-Retarget'] = 'body'
        return resp
    

def init_jwt_error_handlers(app):
    pass
    # @jwt.expired_token_loader
    # def expired_token_callback(jwt_header, jwt_data):
    #     flash("Token has expired", "error")
    #     return resolve_redirect('/auth')

    # @jwt.invalid_token_loader
    # def invalid_token_callback(error):
    #     flash("Invalid Token", "error")
    #     return resolve_redirect('/auth')

    # @jwt.unauthorized_loader
    # def unauthorized_callback(error):
    #     flash("Unauthorized", "error")
    #     return resolve_redirect('/auth')

    # claims
    # @jwt.additional_claims_loader
    # def add_claims_to_access_token(identity):
    #     claims = {}
    #     user = User.get_by_id(identity)
    #     if user:
    #         claims['role'] = user.role
    #     return claims

    # # user loader
    # @jwt.user_lookup_loader
    # def user_lookup_callback(_jwt_header, jwt_data):
    #     identity = jwt_data["sub"]
    #     return User.get_by_email(identity)

    # @jwt.token_in_blocklist_loader
    # def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    #     jti = jwt_payload["jti"]
    #     return TokenBlocklist.test_token_revoked(jti)

    # # implicit refresh token
    # @app.after_request
    # def refresh_expiring_jwts(response):
    #     try:
    #         exp_timestamp = get_jwt()["exp"]
    #         now = datetime.now(timezone.utc)
    #         target_timestamp = datetime.timestamp(now + timedelta(minutes=15))
    #         if target_timestamp > exp_timestamp:
    #             access_token = create_access_token(identity=get_jwt_identity())
    #             TokenBlocklist.add_token(TokenBlocklist(jti=get_jwt()["jti"], type="access", user_id=jwt_current_user.id))
    #             set_access_cookies(response, access_token)
    #         return response
    #     except (RuntimeError, KeyError):
    #         # Case where there is not a valid JWT. Just return the original response
    #         return response