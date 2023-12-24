from flask_wtf import FlaskForm
from flask_babelex import lazy_gettext as l_
from wtforms import StringField, PasswordField, EmailField,  DateField, SubmitField, SelectField, RadioField, IntegerField
from wtforms.widgets import FileInput
from wtforms_alchemy import PhoneNumberField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError, Optional
from markupsafe import Markup
import re
from datetime import datetime
from general_bp.forms import customDR, Validator, Formatter, OrderedForm, ProfileCommonFields, PasswordFields


class AuthForm(FlaskForm):
    email = EmailField(l_('Enter email'), validators=[customDR(), Email()], filters=[Formatter.format_lower], )
    continue_auth = SubmitField(l_('Continue'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # add the base name property to display on error messages for inline errors
        setattr(self.email, 'basename', 'Email')

class CodeForm(FlaskForm):
    d1 = StringField(validators=[customDR()], render_kw={'maxlength': '1', 'minlength': '1', 'pattern': r'\d*', 'inputmode': 'numeric'})
    d2 = StringField(validators=[customDR()], render_kw={'maxlength': '1', 'minlength': '1', 'pattern': r'\d*', 'inputmode': 'numeric'})
    d3 = StringField(validators=[customDR()], render_kw={'maxlength': '1', 'minlength': '1', 'pattern': r'\d*', 'inputmode': 'numeric'})
    d4 = StringField(validators=[customDR()], render_kw={'maxlength': '1', 'minlength': '1', 'pattern': r'\d*', 'inputmode': 'numeric'})

class NameForm(FlaskForm, ProfileCommonFields):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
   
class LoginPasswordForm(FlaskForm):
    password = PasswordField(l_('Password'), validators=[customDR()])

# REGISTER FORM
class UpdateEmailForm(FlaskForm):
    email = EmailField(l_('Email'), validators=[customDR(), Email()], filters=[Formatter.format_lower])
    update = SubmitField(l_('Update'))

# Reset Passowrd
class ResetPasswordForm(OrderedForm, PasswordFields):
    old_password = PasswordField(l_('Old Password'), validators=[customDR()])
    reset = SubmitField(l_('Reset Password'))
    _order = ('csrf_token', 'old_password', 'password', 'conf_password', 'reset')


