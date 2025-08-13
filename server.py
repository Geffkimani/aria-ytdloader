"""
Run uvicorn in a background thread and attach GUI instance.
Provides clean shutdown via Server.shutdown()
"""
import uvicorn
import threading
import logging
from api import app

logger = logging.getLogger(__name__)

class Server(threading.Thread):
    def __init__(self, app_instance, host="127.0.0.1", port=5000):
        super().__init__(daemon=True, name="FastAPIServerThread")
        self.app_instance = app_instance
        self.host = host
        self.port = port
        self._server = None
        app.state.app_instance = self.app_instance
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)

    def run(self):
        logger.info("Starting uvicorn server at %s:%s", self.host, self.port)
        try:
            self._server.run()
        except Exception:
            logger.exception("uvicorn server crashed")

    def shutdown(self):
        if self._server:
            logger.info("Requesting server shutdown")
            self._server.should_exit = True