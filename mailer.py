# encoding: utf-8
import smtplib
import ssl
import socket
from email.message import EmailMessage
from smtplib import (SMTP, SMTP_SSL, SMTPException, SMTPRecipientsRefused,
                     SMTPSenderRefused, SMTPServerDisconnected)
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



_all__ = [
        'MailException',
        'MailConfigurationException',
        'TransportException',
        'TransportFailedException',
        'MessageFailedException',
        'TransportExhaustedException',
        'ManagerException'
    ]



class MailException(Exception):
    """The base for amailer exceptions."""
    
    pass


# Application Exceptions

class DeliveryException(MailException):
    """The base class for all public-facing exceptions."""
    
    pass


class DeliveryFailedException(DeliveryException):
    """The message stored in args[0] could not be delivered for the reason
    given in args[1].  (These can be accessed as e.msg and e.reason.)"""
    
    def __init__(self, message, reason):
        self.msg = message
        self.reason = reason
        
        super(DeliveryFailedException, self).__init__(message, reason)


# Internal Exceptions

class MailerNotRunning(MailException):
    """Raised when attempting to deliver messages using a dead interface."""
    
    pass


class MailConfigurationException(MailException):
    """There was an error in the configuration of marrow.mailer."""
    
    pass


class TransportException(MailException):
    """The base for all marrow.mailer Transport exceptions."""
    
    pass


class TransportFailedException(TransportException):
    """The transport has failed to deliver the message due to an internal
    error; a new instance of the transport should be used to retry."""
    
    pass


class MessageFailedException(TransportException):
    """The transport has failed to deliver the message due to a problem with
    the message itself, and no attempt should be made to retry delivery of
    this message.  The transport may still be re-used, however.
    
    The reason for the failure should be the first argument.
    """
    
    pass


class TransportExhaustedException(TransportException):
    """The transport has successfully delivered the message, but can no longer
    be used for future message delivery; a new instance should be used on the
    next request."""
    
    pass



class Mailer(object):
    def __init__(self, hostname, smtp_port, smtp_username, smtp_password, from_email):
        self.host = hostname
        self.port = smtp_port
        self.username = smtp_username
        self.password = smtp_password
        self.from_email = from_email
        self.connection = None
        if not self.connected:
            self.connect()

    def disconnect(self):
        if self.connected:
            try:
                self.connection.quit()
            except SMTPServerDisconnected: 
                pass
            except (SMTPException, socket.error): 
                raise SMTPException
            finally:
                self.connection = None

    def connect(self):
        ssl_context = ssl.create_default_context()
        connection = SMTP_SSL(
            host=self.host, port=self.port, context=ssl_context)
        connection.ehlo()
        connection.login(self.username, self.password)
        self.connection = connection

    @property
    def connected(self):
        return getattr(self.connection, 'sock', None) is not None

    def send(self, data, recipients:list, cc:list=[], bcc:list=[]):
        if not recipients:
            raise ValueError(f'Expected one or more recipients got {len(recipients)}')
        if not self.connected:
            self.connect()

        try:
            self.send_with_smtp(data, recipients=recipients, cc=cc, bcc=bcc)
        except Exception:
            raise TransportExhaustedException()
    def send_with_smtp(self, data, recipients:list, cc:list=[], bcc:list=[]):
        print(cc, bcc)
        try:
            message = MIMEMultipart("alternative")
            message['Subject'] = data.get('subject')
            message['From'] = self.from_email
            message['To'] = ','.join(recipients)
            message['CC'] = ','.join(cc) if cc  else ''
            message['BCC'] = ','.join(bcc) if bcc else ''
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            message.attach(MIMEText(data.get('plain_content'), 'plain'))
            message.attach(MIMEText(data.get('html_content'), 'html'))
            self.connection.sendmail(from_addr=self.from_email, to_addrs=recipients, msg=message.as_string())

        except SMTPSenderRefused as e:
            raise MessageFailedException(str(e))

        except SMTPRecipientsRefused as e:
            raise MessageFailedException(str(e))

        except SMTPServerDisconnected as e:  
            raise TransportFailedException()

        except Exception as e:  
            cls_name = e.__class__.__name__
            raise TransportFailedException()
