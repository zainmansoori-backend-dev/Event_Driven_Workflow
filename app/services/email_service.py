# email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import logging

load_dotenv(".env")
logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[list] = None,
        bcc: Optional[list] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            
            # Add plain text part
            msg.attach(MIMEText(body, "plain"))
            
            # Add HTML part if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            # Send email
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            server.send_message(msg, to_addrs=recipients)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def send_email_from_template(
        self,
        to_email: str,
        template_data: Dict[str, Any],
        subject_template: Optional[str] = None,
        body_template: Optional[str] = None
    ) -> bool:
        """
        Send email using template data
        
        Args:
            to_email: Recipient email address
            template_data: Dictionary with template variables
            subject_template: Subject template (supports {variable} substitution)
            body_template: Body template (supports {variable} substitution)
            
        Returns:
            True if sent successfully, False otherwise
        """
        subject = subject_template or "Notification"
        body = body_template or "You have a new notification."
        
        # Simple template substitution
        try:
            subject = subject.format(**template_data)
            body = body.format(**template_data)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
        
        return self.send_email(to_email, subject, body)

