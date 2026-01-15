from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Optional, Any, Dict
import json
import logging
import os
import threading
import urllib.parse

logger = logging.getLogger("FireflyAPI")

class APIResponseManager:
    @staticmethod
    def json(handler, data, status=200):
        handler.send_response(status)
        handler.send_header('Content-type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*') # Enable CORS for IDE frontend
        handler.end_headers()
        handler.wfile.write(json.dumps(data).encode('utf-8'))

    @staticmethod
    def error(handler, message, status=404):
        APIResponseManager.json(handler, {"error": message}, status)

class APIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for artifacts and status."""
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')

        if not path_parts or path_parts[0] != 'api':
            APIResponseManager.error(self, "Not Found", 404)
            return

        # /api/artifacts
        if len(path_parts) == 2 and path_parts[1] == 'artifacts':
            self.handle_list_sessions()

        # /api/artifacts/{session_id}
        elif len(path_parts) == 3 and path_parts[1] == 'artifacts':
            self.handle_list_artifacts(path_parts[2])

        # /api/artifacts/{session_id}/{filename}
        elif len(path_parts) == 4 and path_parts[1] == 'artifacts':
            self.handle_get_artifact(path_parts[2], path_parts[3])

        # /api/status
        elif len(path_parts) == 2 and path_parts[1] == 'status':
            self.handle_get_status()

        # /api/usage
        elif len(path_parts) == 2 and path_parts[1] == 'usage':
            self.handle_get_usage()

        else:
            APIResponseManager.error(self, "Endpoint not found", 404)

    def handle_list_sessions(self):
        artifact_service = self.server.artifact_service
        base_dir = artifact_service.artifact_base_dir

        if not base_dir.exists():
            APIResponseManager.json(self, [])
            return

        sessions = [d.name for d in base_dir.iterdir() if d.is_dir()]
        APIResponseManager.json(self, sorted(sessions, reverse=True))

    def handle_list_artifacts(self, session_id):
        artifact_service = self.server.artifact_service
        session_dir = artifact_service.artifact_base_dir / session_id

        if not session_dir.exists():
            APIResponseManager.error(self, "Session not found")
            return

        artifacts = []
        for file in sorted(session_dir.glob("*.json")):
            artifacts.append({
                "name": file.name,
                "type": file.name.split('-')[-1].replace('.json', ''),
                "path": f"/api/artifacts/{session_id}/{file.name}"
            })
        APIResponseManager.json(self, artifacts)

    def handle_get_artifact(self, session_id, filename):
        artifact_service = self.server.artifact_service
        file_path = artifact_service.artifact_base_dir / session_id / filename

        if not file_path.exists() or not file_path.is_file():
            APIResponseManager.error(self, "Artifact not found")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            APIResponseManager.json(self, data)
        except Exception as e:
            APIResponseManager.error(self, f"Error reading artifact: {str(e)}", 500)

    def handle_get_status(self):
        # This could be expanded to include more runtime info
        status = {
            "status": "online",
            "version": "1.0.0",
            "capabilities": ["browser", "memory", "artifacts", "triggers", "usage_api"]
        }
        APIResponseManager.json(self, status)

    def handle_get_usage(self):
        # Access the model client manager via the server
        model_client = self.server.model_client
        if model_client:
            APIResponseManager.json(self, model_client.usage_ledger)
        else:
            APIResponseManager.error(self, "Model client not available", 500)

    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to stdout to keep Firefly logs clean
        logger.debug(format % args)

class APIController:
    """
    Manages the HTTP API Server.
    """
    def __init__(self, event_bus, artifact_service=None, model_client=None, port=5000):
        self.port = port
        self.server = None
        self.thread = None
        self.event_bus = event_bus
        self.artifact_service = artifact_service
        self.model_client = model_client

    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"API Controller started on port {self.port}")

    def _run(self):
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), APIRequestHandler)
            # Inject services into server for handler access
            self.server.artifact_service = self.artifact_service
            self.server.model_client = self.model_client
            self.server.event_bus = self.event_bus

            self.server.serve_forever()
        except Exception as e:
            logger.error(f"API Server failed: {e}")

    def stop(self):
        """Stop the API server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Firefly API server stopped")
