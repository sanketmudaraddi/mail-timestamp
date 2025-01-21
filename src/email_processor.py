import cups 
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from datetime import datetime
import os
from pathlib import Path
import json
import asyncio
from email import policy
from email.parser import BytesParser

class EmailProcessor:
    def __init__(self):
        self.printer_conn = cups.Connection()
        self.smtp_host = os.getenv('SMTP_HOST', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_address = os.getenv('FROM_ADDRESS', 'noreply@timestampservice.com')

    async def process_email(self, message, metadata, sender, recipients):
        """Process a received email by printing it and sending acknowledgment."""
        try:
            # Print the email
            await self.print_email(message, metadata)
            
            # Send acknowledgment
            await self.send_acknowledgment(message, metadata, sender)
            
        except Exception as e:
            print(f"Error processing email: {e}")
            raise

    async def print_email(self, message, metadata):
        """Print the email with timestamp information."""
        try:
            # Create a temporary file for printing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                # Write timestamp information
                temp_file.write(f"=== Email Timestamp Information ===\n")
                temp_file.write(f"Received: {metadata['timestamp']}\n")
                temp_file.write(f"From: {metadata['from']}\n")
                temp_file.write(f"To: {', '.join(metadata['to'])}\n")
                temp_file.write(f"Subject: {metadata['subject']}\n")
                temp_file.write("=" * 40 + "\n\n")
                
                # Write email content
                if message.is_multipart():
                    for part in message.walk():
                        if part.get_content_type() == "text/plain":
                            temp_file.write(part.get_payload(decode=True).decode())
                else:
                    temp_file.write(message.get_payload(decode=True).decode())

            # Print the file
            printer_name = self.get_default_printer()
            if printer_name:
                self.printer_conn.printFile(
                    printer_name,
                    temp_file.name,
                    f"Email_{metadata['timestamp']}",
                    {}
                )
            
            # Clean up temporary file
            os.unlink(temp_file.name)
            
        except Exception as e:
            print(f"Error printing email: {e}")
            raise

    def get_default_printer(self):
        """Get the default printer name."""
        printers = self.printer_conn.getPrinters()
        if not printers:
            raise Exception("No printers found")
        
        default_printer = self.printer_conn.getDefault()
        if default_printer:
            return default_printer
        
        # If no default printer, use the first available one
        return list(printers.keys())[0]

    async def send_acknowledgment(self, original_message, metadata, recipient):
        """Send an acknowledgment email with timestamp information."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_address
            msg['To'] = recipient
            msg['Subject'] = f"Receipt Confirmation - {metadata['subject']}"

            # Create acknowledgment body
            body = f"""
            This is an automated acknowledgment of your email.
            
            Timestamp Information:
            ---------------------
            Received: {metadata['timestamp']}
            Original Subject: {metadata['subject']}
            Reference ID: {metadata['filename']}
            
            Your original message has been received, timestamped, and securely stored.
            
            Original Message:
            ----------------
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach the original message
            if original_message.is_multipart():
                for part in original_message.walk():
                    if part.get_content_type() == "text/plain":
                        msg.attach(MIMEText("\n" + part.get_payload(decode=True).decode(), 'plain'))
            else:
                msg.attach(MIMEText("\n" + original_message.get_payload(decode=True).decode(), 'plain'))

            # Send the email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

        except Exception as e:
            print(f"Error sending acknowledgment: {e}")
            raise 