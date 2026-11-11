"""Shared test helpers: config dicts and a file server that supports Range requests."""
import copy
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from lightsout import config


def make_cfg(tmp_path, **over):
    cfg = config.load_config(root=tmp_path, env={})
    cfg["port"] = 0
    cfg["content_dir"] = Path(tmp_path) / "content"
    cfg["content_dir"].mkdir(exist_ok=True)
    cfg["open_browser"] = False
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k] = {**cfg[k], **v}
        else:
            cfg[k] = v
    return cfg


class FileServer:
    """Serves a dict {url path: bytes} with Range support, optional per-path failures."""

    def __init__(self, files):
        self.files = files
        self.hits = []
        outer = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *a):
                pass

            def do_HEAD(self):
                self.do_GET()

            def do_GET(self):
                outer.hits.append((self.command, self.path, self.headers.get("Range")))
                data = outer.files.get(self.path)
                if data is None:
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if isinstance(data, str):
                    data = data.encode()
                start, code = 0, 200
                m = re.match(r"bytes=(\d+)-", self.headers.get("Range") or "")
                if m:
                    start, code = int(m.group(1)), 206
                body = data[start:]
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                if code == 206:
                    self.send_header("Content-Range", "bytes %d-%d/%d" % (start, len(data) - 1, len(data)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.srv.daemon_threads = True
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d/" % self.srv.server_address[1]

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()
