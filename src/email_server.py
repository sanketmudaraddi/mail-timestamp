import asyncio
import email
from datetime import datetime
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP
from pathlib import Path
import json
import os
from email_processor import EmailProcessor

class TimestampingEmailHandler:
    def __init__(self):
        self.storage_path = Path("email_storage")
        self.storage_path.mkdir(exist_ok=True)
        self.email_processor = EmailProcessor()

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        try:
            received_time = datetime.utcnow()
            
            # Parse the email message
            message = email.message_from_bytes(envelope.content)
            
            # Generate unique filename based on timestamp
            timestamp_str = received_time.strftime('%Y%m%d_%H%M%S_%f')
            filename = f"email_{timestamp_str}.eml"
            
            # Save the original email
            email_path = self.storage_path / filename
            with open(email_path, 'wb') as f:
                f.write(envelope.content)
            
            # Save metadata
            metadata = {
                'timestamp': received_time.isoformat(),
                'from': envelope.mail_from,
                'to': envelope.rcpt_tos,
                'subject': message.get('subject', ''),
                'filename': filename
            }
            
            metadata_path = self.storage_path / f"{filename}.meta.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Process the email (print, send acknowledgment, etc.)
            await self.email_processor.process_email(
                message,
                metadata,
                envelope.mail_from,
                envelope.rcpt_tos
            )
            
            return '250 Message accepted for delivery'
        except Exception as e:
            print(f"Error processing email: {e}")
            return '500 Error processing message'

class EmailServer:
    def __init__(self, host='0.0.0.0', port=25):
        self.host = host
        self.port = port
        self.handler = TimestampingEmailHandler()
        self.controller = None

    def start(self):
        self.controller = Controller(
            self.handler,
            hostname=self.host,
            port=self.port
        )
        self.controller.start()
        print(f"Email server running on {self.host}:{self.port}")

    def stop(self):
        if self.controller:
            self.controller.stop()

if __name__ == '__main__':
    server = EmailServer()
    try:
        server.start()
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        server.stop() 