from flask_wtf import FlaskForm
from flask_babelex import lazy_gettext as l_
from wtforms import StringField, PasswordField, EmailField,  DateField, SubmitField, SelectField, RadioField, IntegerField, HiddenField
from wtforms.widgets import FileInput
from wtforms_alchemy import PhoneNumberField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError, Optional
from markupsafe import Markup
import re
from datetime import datetime, time, timedelta
from general_bp.forms import customDR, Validator, Formatter, OrderedForm, CustomDateField


class RideForm(FlaskForm):
    pickup = StringField(l_('Pickup location'), validators=[customDR(), Length(min=1), Validator.validate_name], filters=[Formatter.format_title])
    dropoff = StringField(l_('Dropoff location'), validators=[customDR(), Length(min=1), Validator.validate_name], filters=[Formatter.format_title])
    pickup_details = StringField(l_("Pickup Now"), validators=[customDR(), ], render_kw={'readonly': True, 'disabled': True, 'data-value':'now'})
    search = SubmitField(l_('Search'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pickup_details_as_datetime = None

    def validate_pickup_details(form, field):
          # Parse the string into a datetime object
        if field.data.lower() != 'now':
            try:
                pickup_datetime = datetime.strptime(field.data, "%b %d at %I:%M %p")
                # pickup_datetime = l_("Pickup ")  + pickup_datetime_val
            except ValueError:
                raise ValidationError(l_('Invalid pickup details'))
        else:
            pickup_datetime = datetime.now()

        form.pickup_details_as_datetime = pickup_datetime

class RideDetailsForm(FlaskForm):

    today = datetime.today().date()
    max_date = today + timedelta(days=90)
    pickup_date = CustomDateField(l_('Today'), validators=[customDR(), ], render_kw={'datepicker-mindate': today.strftime(CustomDateField.date_format),
                                                                                 'datepicker_maxdate': max_date.strftime(CustomDateField.date_format),
                                                                                 'datepicker-buttons':'',
                                                                                 'datepicker-activecolor':'gray',
                                                                                 'datepicker-orientation':'left center'
                                                                                 })
    pickup_time = SelectField(l_('Pickup Time'), validators=[customDR(), ])
    next = SubmitField(l_('Next'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_time_choices()
        self.pickup_time.choices = self.time_choices

    def update_time_choices(self):
        is_today = datetime.strptime(self.pickup_date.data, CustomDateField.date_format).date() == datetime.today().date()
        self.time_choices = [l_("Now")] if is_today else []
        for hour in range(24):
            for min_inc in range(0, 6):
                minute = min_inc * 10
                output_time = time(hour, minute) 
                if is_today:
                    if output_time > datetime.now().time():
                        self.time_choices.append(output_time.strftime('%I:%M %p'))
                else:
                    self.time_choices.append(output_time.strftime('%I:%M %p'))
    

    # DEFINED CONSTRAINT TO WORK WITH DATES ONLY
    def validate_pickup_date(cls, field):

        to_date = datetime.strptime(field.data, CustomDateField.date_format)
        if not to_date:
            raise ValidationError(l_('Invalid date format'))
        
        to_date = to_date.date()
        if to_date < cls.today:
            raise ValidationError(l_('Pick-up date must be in the future'))
        
        if to_date > cls.max_date:
            raise ValidationError(l_('Pick-up date must be within 90 days'))

        field.data = to_date # convert to date object
        
    def validate_pickup_time(cls, field):
        current_date_time = datetime.now()
        
        if field.data.lower() != "now":
            pickup_time = datetime.strptime(field.data, '%I:%M %p').time()
            pickup_date_time = datetime.combine(cls.pickup_date.data, pickup_time)

            if pickup_date_time < current_date_time:
                raise ValidationError(l_('Pick-up time must be in the future'))
            else:
                field.data = pickup_time
        else:
            cls.pickup_date.data = current_date_time.date()