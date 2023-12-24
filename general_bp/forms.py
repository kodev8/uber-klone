from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_babelex import lazy_gettext as l_, get_locale
from wtforms import StringField, PasswordField, EmailField, TextAreaField, SubmitField, SelectField, RadioField, IntegerField
from wtforms.widgets import FileInput
from wtforms_alchemy import PhoneNumberField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError, Optional
from markupsafe import Markup
import re
from datetime import datetime
from wtforms.widgets.core import html_params
from utils.config import Files

class Formatter():
    
    """Custom formatter class to format form fields"""

    def format_lower(name):
        return name.lower().strip() if isinstance(name, str) else name
    
    def format_title(name):
        return re.sub(' +', ' ', name.title()).strip() if isinstance(name, str) else name
    
    def format_strip(name):
        return name.strip() if isinstance(name, str) else name
    
class Validator:

    """Custom validator class to validate form fields"""

    _email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
    _password_pattern = r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[^a-zA-Z0-9\s]).{8,}'
    _name_pattern = r'^[a-zA-z][a-zA-z-.\'\s]*[a-zA-z]?$'
    _username_pattern =r'^[a-zA-z0-9-_\.]+$'

    @staticmethod
    def validate_name(form, name):
        if not re.fullmatch(Validator._name_pattern, name.data):
            raise ValidationError(l_('Invalid name'))

    @staticmethod
    def validate_email(form, email):
        if not re.fullmatch(Validator._email_pattern, email.data):
            raise ValidationError(l_('Invalid email'))

    @staticmethod
    def validate_password(form, password):
        if not re.fullmatch(Validator._password_pattern, password.data):
            raise ValidationError(l_('Password must contain: at least 8 characters, 1 lower case, 1 uppercase, 1 number and 1 special character'))

    @staticmethod
    def validate_username(form, user):
        if not re.fullmatch(Validator._username_pattern, user.data):
            raise ValidationError(l_('Username must only contain letters, numbers, periods and underscores'))


class customDR(DataRequired):

    """Custom Data Required validator to display custom error messages: Extends DataRequired validator"""

    def __init__(self, message=None):
        super().__init__(message)

    def __call__(self, form, field):

        # check if field has a basename attribute to display for custom data required errors #TODO babelize
        field_label = getattr(field, 'basename') if hasattr(field, 'basename') else field.label.text
    
        if self.message is None and field_label:

            self.message = f"{field_label} {l_('is required')}"

        super().__call__(form, field)

class CustomFileWidget(FileInput):

    """Custom widget for file input with label"""

    def __init__(self, tag, with_text=False, accept: list =['*'], label=''):
        super().__init__()
        self.tag = tag
        self.with_text = with_text
        self.accept = accept
        self.label = label

    def __call__(self, field, htmx_props={},  **kwargs):
        
       
        accepted =set()
        for file_type in self.accept:
            accepted.add(f', '.join([f'{Files.MAP[file_type]["pre"]}/{ext}' if file_type else "*" for ext in Files.MAP[file_type]['exts']]))

        accepted = ', '.join(accepted)

        input_props = htmx_props | {'class':'hidden', 'accept':accepted}
        input_html = super().__call__(field, **input_props)
      
        params = html_params(title=field.label.text, **kwargs)
        
        widget_html = f'<{self.tag} {params}>{field.label.text.upper() if self.with_text else ""}</{self.tag}>'


        if self.label is None:
            label_html = f'{input_html}'
        else:
            label_html = f'<label>{widget_html} {input_html}</label>'

        return Markup(label_html)

class CustomDateField(StringField):

    """ Custom Date Field to be used with calendar @kodev/flowbite"""

    date_format = '%Y-%m-%d'

    def __init__(self, label='', validators=[], render_kw={}, **kwargs):
        super().__init__(label, validators, render_kw=render_kw,  **kwargs)
        self.render_kw |= {
                        'inline-datepicker':'', 
                        'datepicker-autohide':'',  
                        'datepicker-format':'yyyy-mm-dd',
                        'datepicker-lang':get_locale(), 
                        }
        


class OrderedForm(FlaskForm):

    """ Ordered Form base class to order fields of classes that extend their own fields """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __iter__(self):
        fields = list(super().__iter__())
        field_dict = {field.id: field for field in fields}
        for field_id in self._order:
            if field_id in field_dict:
                yield field_dict[field_id]


# create sub for address
class ProfileCommonFields:
    fname = StringField(l_('First Name'), validators=[customDR(), Length(min=1, max=50, message=l_("First name must be less than 50 characters")), Validator.validate_name], filters=[Formatter.format_title])
    lname = StringField(l_('Last Name'), validators=[customDR(), Length(min=1, max=50, message=l_("Last name must be less than 50 characters")), Validator.validate_name], filters=[Formatter.format_title])
    # dob = DateField('Date of Birth', validators=[customDR(), ],)

    
    # def validate_dob(form, field):
    #     today = datetime.today()
    #     min_year = today.year - 16
    #     min_age_date = datetime(min_year, today.month, today.day).date()
    #     if field.data >  min_age_date:
    #         raise ValidationError("You must be 16 or older to enter.")

class PasswordFields:
    password = PasswordField(l_('Password'), 
                            validators=[ customDR(), 
                                            EqualTo('conf_password', message=l_("Passwords must match")), 
                                            Validator.validate_password
                                        ]
                                )
    conf_password = PasswordField(l_('Confirm Password'), validators=[customDR()])


