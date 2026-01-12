import imaplib
import smtplib
import email
import logging
import os
import threading
import time
from email.mime.text import MIMEText
from typing import Optional, Dict, Any

logger = logging.getLogger("FireflyEmailService")

class EmailService:
    """
    Service to handle Email (IMAP/SMTP) interactions.
    Polls for new emails and sends responses.
    """
    def __init__(self, event_bus, imap_host: Optional[str] = None, smtp_host: Optional[str] = None):
        self.event_bus = event_bus
        self.imap_user = os.environ.get("EMAIL_USER")
        self.imap_pass = os.environ.get("EMAIL_PASS")
        self.imap_host = imap_host or os.environ.get("IMAP_HOST", "imap.gmail.com")
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.imap_port = int(os.environ.get("IMAP_PORT", 993))
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        
        self.is_running = False
        self.polling_thread = None
        
        # Subscribe to outgoing messages to send them back via Email
        self.event_bus.subscribe("email_output", self.handle_outgoing_message)

    def start(self):
        """Start the polling loop in a background thread."""
        if not self.imap_user or not self.imap_pass:
            logger.warning("EMAIL_USER or EMAIL_PASS not set. EmailService will not run.")
            return

        self.is_running = True
        self.polling_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.polling_thread.start()
        logger.info(f"EmailService started polling {self.imap_host}")

    def stop(self):
        """Stop the polling loop."""
        self.is_running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=1.0)
        logger.info("EmailService stopped.")

    def _poll_loop(self):
        """Internal loop to check for updates."""
        while self.is_running:
            try:
                self._check_emails()
            except Exception as e:
                logger.error(f"Error in Email polling loop: {e}")
                time.sleep(10) # Backoff on error

            time.sleep(30) # Poll interval for emails (less aggressive than telegram)

    def _check_emails(self):
        """Connect to IMAP and check for UNSEEN messages."""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(self.imap_user, self.imap_pass)
            mail.select("inbox")

            # Search for unseen messages
            status, response = mail.search(None, 'UNSEEN')
            if status != 'OK':
                return

            for num in response[0].split():
                status, data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                subject = msg.get("Subject", "")
                from_addr = msg.get("From", "")
                
                # Check for Firefly prefix or specific format
                if "FIREFLY" in subject.upper():
                    body = self._get_email_body(msg)
                    logger.info(f"Received Firefly Email from {from_addr}: {subject}")
                    
                    payload = {
                        "type": "email",
                        "from": from_addr,
                        "subject": subject,
                        "text": body
                    }
                    self.event_bus.publish("email_input", payload)
                
            mail.logout()
        except Exception as e:
            logger.debug(f"IMAP check failed (expected if creds invalid): {e}")

    def _get_email_body(self, msg):
        """Extract body text from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode()
        else:
            return msg.get_payload(decode=True).decode()
        return ""

    def handle_outgoing_message(self, event_type: str, payload: Dict[str, Any]):
        """Handle 'email_output' events -> Send email response."""
        to_addr = payload.get("to")
        text = payload.get("text")
        subject = payload.get("subject", "Firefly Response")

        if to_addr and text:
            self.send_email(to_addr, subject, text)

    def send_email(self, to_addr: str, subject: str, text: str):
        """Send an email using SMTP."""
        if not self.imap_user or not self.imap_pass:
            return

        msg = MIMEText(text)
        msg['Subject'] = subject
        msg['From'] = self.imap_user
        msg['To'] = to_addr

        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.imap_user, self.imap_pass)
            server.send_message(msg)
            server.quit()
            logger.info(f"Email sent to {to_addr}")
        except Exception as e:
            logger.error(f"Failed to send Email: {e}")
