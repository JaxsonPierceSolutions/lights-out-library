"""Local web server: the library pages, a proxy to Kiwix, and a few small JSON endpoints.

Listens on 127.0.0.1 only. There is deliberately no option to change that: the library is
meant for the one computer it runs on.
"""
import argparse
import http.client
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, ask, config, layers

HOST = "127.0.0.1"
SITE_DIR = config.ROOT / "site"
MANIFEST = config.ROOT / "manifest" / "content.json"
CSP = ("default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
       "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; "
       "frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'")
TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".ico": "image/x-icon", ".woff2": "font/woff2",
    ".woff": "font/woff", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg", ".flac": "audio/flac", ".wav": "audio/wav",
    ".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".ogv": "video/ogg", ".mov": "video/quicktime",
    ".pdf": "application/pdf", ".txt": "text/plain; charset=utf-8", ".webmanifest": "application/manifest+json",
}
PROXY_REQUEST_HEADERS = ("Range", "Content-Type", "Accept", "Accept-Encoding", "Accept-Language",
                         "If-None-Match", "If-Modified-Since", "If-Range")
PROXY_RESPONSE_HEADERS = ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "Location",
                          "ETag", "Cache-Control", "Content-Encoding", "Last-Modified", "Vary")
CHUNK = 64 * 1024


class LibraryServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR lets a second program take a port that is already in use, so use the
    # exclusive flag there instead and get a clear "port in use" error.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(cfg, site_dir=None, manifest_path=None):
    srv = LibraryServer((HOST, cfg["port"]), Handler)
    srv.cfg = cfg
    srv.site_dir = Path(site_dir or SITE_DIR).resolve()
    srv.manifest_path = Path(manifest_path or MANIFEST)
    srv.kiwix_base = config.kiwix_base(cfg)
    srv.layer = layers.load(cfg.get("layers"))
    ask.configure(cfg)
    return srv


def _hostport(base):
    u = urllib.parse.urlsplit(base)
    return u.hostname, u.port or 80


def kiwix_book_count(base, timeout=2):
    """Number of books Kiwix reports, or None if it isn't answering."""
    try:
        conn = http.client.HTTPConnection(*_hostport(base), timeout=timeout)
        conn.request("GET", "/kiwix/catalog/v2/entries?count=1")
        r = conn.getresponse()
        text = r.read().decode("utf-8", "ignore")
        conn.close()
    except (OSError, http.client.HTTPException):
        return None
    if r.status != 200:
        return None
    m = re.search(r"<(?:\w+:)?totalResults>\s*(\d+)", text)
    return int(m.group(1)) if m else text.count("<entry>")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "LightsOutLibrary/" + __version__

    def version_string(self):
        return self.server_version

    def log_message(self, fmt, *args):
        if os.environ.get("LIGHTSOUT_VERBOSE"):
            sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if getattr(self, "csp", True):
            self.send_header("Content-Security-Policy", CSP)
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        self.send_text(code, message or self.responses.get(code, ("Error",))[0])

    def send_bytes(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_text(self, code, text):
        self.send_bytes(code, text.encode("utf-8"), "text/plain; charset=utf-8")

    def send_json(self, code, obj):
        self.send_bytes(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def host_ok(self):
        host = (self.headers.get("Host") or "").strip().lower()
        name, _, port = host.rpartition(":")
        if not name or not port.isdigit():  # no port given
            name, port = host, ""
        return name in ("127.0.0.1", "localhost") and port in ("", str(self.server.server_address[1]))

    def dispatch(self):
        self.csp = True
        if not self.host_ok():
            return self.send_text(403, "This library only answers on 127.0.0.1 or localhost.")
        path = urllib.parse.urlsplit(self.path).path
        if path == "/kiwix" or path.startswith("/kiwix/"):
            return self.proxy()
        if path == "/api/status" and self.command in ("GET", "HEAD"):
            return self.api_status()
        if path == "/api/manifest" and self.command in ("GET", "HEAD"):
            return self.api_manifest()
        if path == "/api/layer" and self.command in ("GET", "HEAD"):
            return self.send_json(200, layers.public(self.server.layer))
        if (path == "/files" or path.startswith("/files/")) and self.command in ("GET", "HEAD"):
            return self.files(path)
        if path.startswith("/ask/api/"):
            return self.ask_route(path)
        if self.command == "POST":
            return self.send_text(405, "Not allowed.")
        self.static(path)

    do_GET = do_HEAD = do_POST = dispatch

    def static(self, path):
        rel = urllib.parse.unquote(path)
        parts = [p for p in rel.split("/") if p]
        if any(p.startswith(".") or "\\" in p or ":" in p or "\0" in p for p in parts):  # also hides dotfiles
            return self.send_text(404, "Page not found.")
        target, base = layers.find_file(self.server.layer, self.server.site_dir, parts)
        try:
            if rel.endswith("/") or target.is_dir():
                target = target / "index.html"
            target = target.resolve()
            target.relative_to(base)
            if not target.is_file():
                raise OSError
        except (OSError, ValueError):
            return self.send_text(404, "Page not found.")
        if target.suffix.lower() == ".html":
            text = layers.render(target.read_text(encoding="utf-8"), self.server.layer, target.name if target.parent == base else "")
            return self.send_bytes(200, text.encode("utf-8"), TYPES[".html"])
        self.send_file(target)

    def send_file(self, target):
        """A file, with Range support so audio and video can seek."""
        size = target.stat().st_size
        start, end = 0, size - 1
        m = re.match(r"bytes=(\d*)-(\d*)$", (self.headers.get("Range") or "").strip())
        if m and (m.group(1) or m.group(2)) and size:
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        partial = m is not None and (m.group(1) or m.group(2)) and size
        with open(target, "rb") as f:
            f.seek(start)
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", TYPES.get(target.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(end - start + 1 if size else 0))
            self.send_header("Accept-Ranges", "bytes")
            if partial:
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if self.command == "HEAD":
                return
            left = end - start + 1 if size else 0
            try:
                while left > 0:
                    chunk = f.read(min(CHUNK, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except OSError:
                self.close_connection = True

    def files(self, path):
        """Your own files: a folder listing as JSON (the same shape nginx's autoindex_format json
        gives, so the page works behind either), or the file itself."""
        root = Path(self.server.cfg["files_dir"]).resolve()
        rel = urllib.parse.unquote(path[len("/files"):])
        parts = [p for p in rel.split("/") if p]
        if any(p in (".", "..") or "\\" in p or ":" in p or "\0" in p or p.startswith(".") for p in parts):
            return self.send_text(404, "Not found.")
        target = root.joinpath(*parts)
        try:
            target = target.resolve()
            target.relative_to(root)
        except (OSError, ValueError):
            return self.send_text(404, "Not found.")
        if target.is_dir():
            if not path.endswith("/"):
                self.send_response(301)
                self.send_header("Location", path + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            items = []
            for e in sorted(target.iterdir(), key=lambda e: e.name.lower()):
                if e.name.startswith("."):
                    continue
                try:
                    st = e.stat()
                except OSError:
                    continue  # a broken link
                items.append({"name": e.name, "type": "directory" if e.is_dir() else "file",
                              "mtime": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(st.st_mtime)),
                              **({} if e.is_dir() else {"size": st.st_size})})
            return self.send_json(200, items)
        if path == "/files/" or path == "/files":
            return self.send_json(200, [])  # no files folder yet
        if not target.is_file():
            return self.send_text(404, "Not found.")
        self.send_file(target)

    def proxy(self):
        self.csp = False  # Kiwix's own viewer needs scripts and frames that our policy would block
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        up = _hostport(self.server.kiwix_base)
        headers = {k: self.headers[k] for k in PROXY_REQUEST_HEADERS if self.headers.get(k)}
        headers["Host"] = "%s:%s" % up
        conn = http.client.HTTPConnection(*up, timeout=120)
        try:
            conn.request(self.command, self.path, body, headers)
            resp = conn.getresponse()
        except (OSError, http.client.HTTPException):
            conn.close()
            self.csp = True
            return self.send_text(503, "The book server (Kiwix) is not running right now. "
                                       "Restart the library, or run fetch to get books and the book server.")
        try:
            self.send_response(resp.status)
            for k in PROXY_RESPONSE_HEADERS:
                if resp.getheader(k):
                    self.send_header(k, resp.getheader(k))
            if resp.getheader("Content-Length") is None:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            if self.command != "HEAD" and resp.status not in (204, 304):
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (OSError, http.client.HTTPException):
            self.close_connection = True
        finally:
            conn.close()

    def api_status(self):
        cfg = self.server.cfg
        count = kiwix_book_count(self.server.kiwix_base)
        manifest = _load_json(self.server.manifest_path)
        self.send_json(200, {
            "version": __version__,
            "books": count or 0,
            "kiwix": count is not None,
            "ask": {"enabled": cfg["ask"]["enabled"], "model": cfg["ask"]["model"]},
            "content_bytes": sum(p.stat().st_size for p in config.find_zims(cfg["content_dir"])),
            "limit_gb": manifest.get("limit_gb", 500),
        })

    def api_manifest(self):
        manifest = _load_json(self.server.manifest_path)
        names = [p.name for p in config.find_zims(self.server.cfg["content_dir"])]
        for item in manifest.get("items", []):
            item["have"] = any(n.startswith(item["id"] + "_") for n in names)
        self.send_json(200, manifest)

    def ask_route(self, path):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(min(length, 20000)) if length else b""
        if not self.server.cfg["ask"]["enabled"]:
            return self.send_json(404, {"error": "Ask is turned off"})
        if path == "/ask/api/health" and self.command == "GET":
            return self.send_json(200, ask.health())
        if path == "/ask/api/ask" and self.command == "POST":
            return ask.handle_ask(self, body)
        self.send_json(404, {"error": "not found"})


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def fetch_command():
    return "fetch.cmd" if os.name == "nt" else "./fetch.sh"


def find_kiwix_serve(root):
    tools = Path(root) / "tools" / "kiwix"
    if tools.is_dir():
        for p in sorted(tools.rglob("kiwix-serve*")):
            if p.is_file() and p.name in ("kiwix-serve.exe", "kiwix-serve"):
                return str(p)
    return shutil.which("kiwix-serve")


def port_in_use(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, port)) == 0


class KiwixProcess:
    def __init__(self, exe, zims, port, log_path):
        self.log_path = log_path
        self.log = open(log_path, "wb")
        cmd = [exe, "--address", HOST, "--port", str(port), "--urlRootLocation", "/kiwix"] + [str(z) for z in zims]
        self.proc = subprocess.Popen(cmd, stdout=self.log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)

    def wait_ready(self, base, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if self.proc.poll() is not None:
                return False
            if kiwix_book_count(base, timeout=1) is not None:
                return True
            time.sleep(0.3)
        return False

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(8)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.log.close()


def _raise_interrupt(signum, frame):
    raise KeyboardInterrupt


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lightsout", description="Lights Out Library: start the offline library.")
    ap.add_argument("--port", type=int, help="port for the library pages (default 8600)")
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser")
    ap.add_argument("--content", metavar="DIR", help="folder that holds the .zim book files")
    ap.add_argument("--layer", metavar="DIR", action="append", help="add-on layer folder (see docs/layers.md); repeat to stack")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)  # so messages appear at once even when output is redirected
    try:
        cfg = config.load_config()
    except config.ConfigError as e:
        print("Settings problem: %s" % e)
        return 1
    if args.port:
        cfg["port"] = args.port
    if args.content:
        cfg["content_dir"] = Path(args.content).resolve()
    if args.no_browser:
        cfg["open_browser"] = False
    if args.layer:
        cfg["layers"] = [Path(x).resolve() for x in args.layer]

    try:
        srv = make_server(cfg)
    except layers.LayerError as e:
        print("Layer problem: %s" % e)
        return 1
    except OSError:
        print("Port %d is already in use, so the library cannot start.\n"
              "The library may already be running (check your browser tabs and any open black windows),\n"
              "or another program is using that port. Close it, or start with: --port 8700" % cfg["port"])
        return 1

    kiwix = None
    zims = config.find_zims(cfg["content_dir"])
    exe = None if cfg["kiwix_url"] else find_kiwix_serve(cfg["root"])
    if cfg["kiwix_url"]:
        print("Using the book server at %s." % cfg["kiwix_url"])
    elif not zims:
        print("No books found in %s.\nThe pages will open, but search is empty. To get books, run:\n    %s --tier pocket"
              % (cfg["content_dir"], fetch_command()))
    elif not exe:
        print("The book server (Kiwix) is not installed yet. To get it, run:\n    %s --tools" % fetch_command())
    elif port_in_use(cfg["kiwix_port"]):
        print("Port %d (for the book server) is already in use, so books are unavailable.\n"
              "Close the other copy of the library, or set kiwix_port in config.json." % cfg["kiwix_port"])
    else:
        print("Starting the book server with %d book%s ..." % (len(zims), "" if len(zims) == 1 else "s"))
        kiwix = KiwixProcess(exe, zims, cfg["kiwix_port"], cfg["root"] / "kiwix-serve.log")
        if not kiwix.wait_ready(srv.kiwix_base):
            print("The book server did not start. Details are in %s. The pages will still open." % kiwix.log_path)

    url = "http://%s:%d/" % (HOST, srv.server_address[1])
    print("\nLights Out Library is running.\nOpen %s in your browser.\nTo stop it, press Ctrl+C in this window.\n" % url)
    signal.signal(signal.SIGTERM, _raise_interrupt)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _raise_interrupt)
    if cfg["open_browser"]:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Stopping ...")
    finally:
        srv.server_close()
        if kiwix:
            kiwix.stop()
    return 0
