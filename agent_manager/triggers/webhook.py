from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional
import json
import logging



logger = logging.getLogger("FireflyWebhook")

class WebhookRequestLogic(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle incoming webhook POST requests."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            if not post_data:
                 self.send_response(400)
                 self.end_headers()
                 return

            payload = json.loads(post_data.decode('utf-8'))
            logger.info(f"Received webhook payload: {payload}")

            # Access injected event bus from the server instance
            if hasattr(self.server, 'event_bus') and self.server.event_bus:
                self.server.event_bus.publish("webhook_event", payload)
            else:
                logger.error("EventBus not attached to Webhook Server!")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "received"}).encode('utf-8'))

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.end_headers()

class WebhookService:
    def __init__(self, event_bus, port: int = 5000):
        self.port = port
        self.event_bus = event_bus
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None

    def start(self):
        """Start the webhook server in a separate thread."""
        self.server = HTTPServer(('0.0.0.0', self.port), WebhookRequestLogic)
        # Inject event_bus into the server instance so the handler can access it
        self.server.event_bus = self.event_bus
        
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Webhook server started on port {self.port}")

    def stop(self):
        """Stop the webhook server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Webhook server stopped")
