"""A tiny stand-in for Ollama: /api/tags, /api/embed, /api/generate (plain and streaming)."""
import hashlib
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANSWER = ["Boil it ", "for one minute. ", "[1]"]


def vec(text, dims=24):
    v = [0.0] * dims
    for w in re.findall(r"[a-z]+", text.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dims] += 1.0
    return v


def start(requests):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *a):
            pass

        def send(self, obj):
            data = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/api/tags":
                return self.send({"models": [{"name": "testmodel:1b"}]})
            self.send_error(404)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, body))
            if self.path == "/api/embed":
                return self.send({"embeddings": [vec(t) for t in body["input"]]})
            if self.path == "/api/generate" and body.get("stream"):
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                for piece in ANSWER:
                    self.wfile.write((json.dumps({"response": piece, "done": False}) + "\n").encode())
                self.wfile.write((json.dumps({"response": "", "done": True}) + "\n").encode())
                return
            if self.path == "/api/generate":
                return self.send({"response": json.dumps({"queries": ["purify water", "water boiling"], "medical": False})})
            self.send_error(404)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]
