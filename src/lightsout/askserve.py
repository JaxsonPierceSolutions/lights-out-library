"""Ask on its own: the AI answer service without the library pages.

For a library whose pages are served some other way (for example by nginx after
``python -m lightsout.build``), run this beside it and send ``/ask/api/`` to it:

    python -m lightsout.askserve --port 8095

It reads the same config.json as the library (ask.enabled must be true, and ask.model set).
Like the library, it listens on 127.0.0.1 only. A web server on the same computer can pass
requests on to it; it never answers another machine directly.

It answers ``GET /health`` and ``POST /ask``, and the same under ``/ask/api/``, so it works
whether or not the web server in front strips that prefix.
"""
import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import ask, config

HOST = "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "LightsOutAsk"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (time.strftime("%F %T"), fmt % args))

    def _route(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/ask/api/"):
            path = path[len("/ask/api"):]
        return path

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self._route() == "/health":
            return self._json(200, ask.health())
        self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(min(length, 20000)) if length else b""
        if self._route() == "/ask":
            return ask.handle_ask(self, body)
        self._json(404, {"error": "not found"})


def make_server(cfg, port):
    ask.configure(cfg)
    srv = ThreadingHTTPServer((HOST, port), Handler)
    srv.daemon_threads = True
    return srv


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lightsout.askserve", description="Run Ask (local AI answers) on its own.")
    ap.add_argument("--port", type=int, default=8095, help="port on 127.0.0.1 (default 8095)")
    ap.add_argument("--root", help="folder that holds config.json (default: this project)")
    args = ap.parse_args(argv)
    try:
        cfg = config.load_config(root=args.root) if args.root else config.load_config()
    except config.ConfigError as e:
        print("Settings problem: %s" % e)
        return 1
    if not cfg["ask"]["enabled"]:
        print("Ask is turned off. Set ask.enabled to true and ask.model in config.json.")
        return 1
    srv = make_server(cfg, args.port)
    print("Ask is answering on http://%s:%d/ (model %s)." % (HOST, args.port, cfg["ask"]["model"]), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
