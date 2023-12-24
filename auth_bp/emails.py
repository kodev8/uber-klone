from __future__ import print_function
# import sib_api_v3_sdk
# from sib_api_v3_sdk.rest import ApiException
# from pprint import pprint
from utils.helper import logging
from utils.config import  EMAIL_SENDER, EMAIL_PASSWORD, FLASK_TESTING #, EMAIL_API_KEY
from email.message import EmailMessage
import smtplib
import ssl
# def send_email_brevo(email, content, subject, name=""):
#     """send email with brevo but account is currently suspended"""

#     config = sib_api_v3_sdk.Configuration()
#     config.api_key['api-key'] = EMAIL_API_KEY
#     api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(config))
#     sender= {"name": "Admin @ KUber", "email": EMAIL_SENDER}
#     to=[{"email": email, "name": "T"}]
#     send_email = sib_api_v3_sdk.SendSmtpEmail(to=to, subject=subject, html_content=content, sender=sender)

#     try:
#         api_response = api_instance.send_transac_email(send_email)
#         pprint(api_response)
#         if email == "k@k.c":
#             raise ApiException(status=400, reason="Bad Request")
        
#         return True
#     except Exception as e:
#         # print("Exception when calling EmailCampaignsApi->create_email_campaign: %s\n" % e)
#         return False

def send_email_gmail(email, content, subject, name=""):
    
    """send email with gmail"""

    # print("sending email to ", email)

    try:

        if FLASK_TESTING:
            # print("Not sending email in development")
            return True
        email_message = EmailMessage()
        email_message['From'] = f"Admin - KUber <{EMAIL_SENDER}>"
        email_message['To'] = email
        email_message['Subject'] = subject
        email_message.set_content(content, subtype='html')

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(email_message)

        logging.info(f"Email sent to {email} successfully", extra={'to':email, 'subject':subject})
        return True
    except Exception as e:
        logging.error(f"ERROR @ send_email_gmail: {e}", exc_info=True, stack_info=True, stacklevel=3, extra={'to':email, 'subject':subject})
        # print("Exception when calling Email Gmail", e)
        return False