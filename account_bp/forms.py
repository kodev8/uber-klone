from flask_wtf import FlaskForm
from flask_babelex import lazy_gettext as l_, get_locale
from wtforms import StringField, PasswordField, EmailField, SubmitField, SelectField, IntegerField, DateField
from flask_wtf.file import FileField, FileAllowed
from wtforms.widgets import FileInput
from wtforms_alchemy import PhoneNumberField
from wtforms.validators import Email,  Regexp, InputRequired, Length, ValidationError
from datetime import datetime
from general_bp.forms import customDR, Formatter, OrderedForm,  PasswordFields, CustomFileWidget, CustomDateField
from auth_bp.forms import NameForm
from utils.config import Files
from utils.extensions import babel
import country_list
from datetime import timedelta

class UpdateNameForm(NameForm):
    update = SubmitField(l_('Update'))
    _order = ('csrf_token', 'fname', 'lname', 'update')


class UpdateEmailForm(FlaskForm):
    email = EmailField(l_('Email'), validators=[customDR(), Email()], filters=[Formatter.format_lower])
    update = SubmitField(l_('Update'))

class UpdatePhoneForm(FlaskForm):
    phone = PhoneNumberField(l_('Phone Number'), validators=[customDR()])
    update = SubmitField(l_('Update'))

# Reset Passowrd
class SetPasswordForm(OrderedForm, PasswordFields):
    old_password = PasswordField(l_('Old Password'), validators=[customDR()])

    reset = SubmitField()

    _order = ('csrf_token', 'old_password', 'password', 'conf_password', 'reset')

    def __init__(self, is_reset:bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # change the label of the reset button
        if is_reset:
            self.reset.label.text = l_('Reset Password')
        else:
            # remove the old password field if not reset
            self._fields.pop('old_password', None)
            self.reset.label.text = l_('Set Password')

        setattr(self.conf_password, 'basename', l_('Password Confirmation'))
        
class ProfilePhotoForm(FlaskForm):
    photo = FileField('Profile Photo', validators=[FileAllowed(Files.IMAGE_EXTS)], 
                      widget=CustomFileWidget('div', accept=('image',)))
    
class AddPayPalForm(FlaskForm):
    email = EmailField('PayPal ' + l_('Email'), validators=[customDR(), Email()], filters=[Formatter.format_lower])
    add = SubmitField(l_('Add'))

class AddCardForm(FlaskForm):
    card_number = StringField(l_('Card Number'), validators=[customDR(), Length(min=19, max=19, message=l_('Card number must be 16 digits')),
        Regexp(r'^\d{4}(\s\d{4}){3}$', message=l_('Format must be') + ' XXXX-XXXX-XXXX-XXXX') # use regex to check format for card number
    ],  filters=[Formatter.format_strip, ])

    expiry_date = StringField('MM/YYYY', validators=[
        Regexp(r'^\d{2}/\d{4}$', message=l_('Format must be MM/YYYY')) # use regex to check format for expiry date
    ])

    cvv = StringField('CVV', validators=[customDR(), Length(min=3, max=3, message=l_('CVV must be 3 digits'))])
    country = SelectField(l_('Country'), validators=[customDR()])
    add = SubmitField(l_('Add'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locale = str(get_locale()) # get the current locale
        if not locale in country_list.available_languages() or not locale: # check if the locale is supported by country_list
            locale = 'en'
            
        self.country.choices = country_list.countries_for_language(locale)
        base_option = ('Select Country', l_('Select Country')) # add a base option to the country select field if not already present
        if base_option not in self.country.choices:
            self.country.choices.insert(0, base_option)
        
    def validate_expiry_date(self, field):

        """ validate the expiry date field """
        try:
            # get the month and year from the field data
            month, year = field.data.split('/')
            month, year = int(month), int(year)
        except ValueError:
            raise ValidationError(l_('Format must be MM/YYYY'))
        
        if month < 1 or month > 12:
            # check if month is valid
            raise ValidationError(l_('Month must be between 1 and 12'))
        if year < datetime.now().year:
            # check if year is less than current year
            raise ValidationError(l_('Year must be in the future'))
        if year == datetime.now().year and month < datetime.now().month:
            # check if year is current year and month is less than current month
            raise ValidationError(l_('Month must be in the future'))
        
    def validate_country(self, field):
        """ validate the country field """
        # make sure the default option is not selected
        if field.data == 'Select Country':
            raise ValidationError(l_('Please select a country'))
        
class AddBankForm(FlaskForm):
    bank_name = StringField(l_('Bank Name'), validators=[customDR(), Length(min=2, max=50,message=l_("Bank Name must be between 2 and 50 characters")),])
    account_number = StringField(l_('Account Number'), validators=[customDR(), Length(min=10, max=50, message=l_("Account number must be between 10 and 50 characters")), Regexp(r'^\d+$')], )
    add = SubmitField(l_('Add'))

class DriverSetupForm(FlaskForm):
    tomorrow = datetime.today().date() + timedelta(days=1)
    stft_tomorrow = tomorrow.strftime(CustomDateField.date_format)
    license_number = StringField(l_('License Number'), validators=[customDR(), Length(min=10, max=10, message=l_('License number must be 10 characters'))])

    license_expiry_date = CustomDateField(l_('License Expiry Date'), validators=[customDR(), ], render_kw={
                                                                                'datepicker-mindate': stft_tomorrow,
                                                                                 'datepicker-activecolor':'gray',
                                                                                 'datepicker-orientation':'left bottom'
                                                                                 })
    
    license_photo = FileField(l_('License Photo'), validators=[FileAllowed(Files.IMAGE_EXTS)], render_kw={'accept':'image/*'})
    vehicle_plate = StringField(l_('Vehicle Plate'), validators=[customDR(), Length(min=7, max=7, message=l_('Vehicle plate must be 7 characters'))])
    vehicle_photo = FileField(l_('Vehicle Photo'), validators=[FileAllowed(Files.IMAGE_EXTS)], render_kw={'accept':'image/*'})
    send = SubmitField(l_('Send'))

    def validate_license_expiry_date(cls, field):

        """ validate the pickup date field """

        # convert the date string to a date object
        to_date = datetime.strptime(field.data, CustomDateField.date_format)
        if not to_date:
            raise ValidationError(l_('Invalid date format'))
        
        #  make sure the date is in the future
        to_date = to_date.date()
        if to_date < datetime.now().date():
            raise ValidationError(l_('License expiry date must be in the future'))

        field.data = to_date # convert to date object
        
        