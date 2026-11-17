"""Run Docket with wsgiref: python -m docket.serve --db PATH [--host H] [--port N]."""
import argparse
import logging
import signal
import socketserver
import sys
import threading
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .app import create_app


class ThreadingWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    """Access log through `logging` without the query string (it can carry filenames)."""

    def log_request(self, code="-", size="-"):
        logging.getLogger("docket.access").info(
            "%s %s %s", self.command, self.path.split("?", 1)[0], code)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m docket.serve")
    parser.add_argument("--db", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = create_app(args.db)
    app.start_worker()
    server = make_server(args.host, args.port, app, server_class=ThreadingWSGIServer,
                         handler_class=QuietHandler)

    def shutdown(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    logging.getLogger("docket").info("listening on %s:%d", args.host, args.port)
    try:
        server.serve_forever()
    finally:
        app.stop_worker()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
