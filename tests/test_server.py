import http.client
import json
import socket
import threading

import pytest

import fake_kiwix
from helpers import make_cfg
from lightsout import server as srvmod

MANIFEST = {"schema": 1, "limit_gb": 500, "items": [
    {"id": "zimgit-water_en", "title": "Water", "tier": "pocket"},
    {"id": "usda-2015_en", "title": "Canning", "tier": "pocket"}]}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Running:
    def __init__(self, tmp_path, kiwix_url, **over):
        self.site = tmp_path / "site"
        self.site.mkdir()
        (self.site / "index.html").write_text("<h1>Home</h1>")
        (self.site / "app.js").write_text("1")
        (self.site / "font.woff2").write_bytes(b"wOF2")
        (tmp_path / "private.txt").write_text("private")
        manifest = tmp_path / "content.json"
        manifest.write_text(json.dumps(MANIFEST))
        self.cfg = make_cfg(tmp_path, kiwix_url=kiwix_url, **over)
        self.srv = srvmod.make_server(self.cfg, self.site, manifest)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, args=(0.05,), daemon=True).start()

    def get(self, path, method="GET", headers=None, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request(method, path, body, headers or {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r, data

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def kiwix():
    srv, base = fake_kiwix.start()
    yield base
    srv.shutdown()


@pytest.fixture
def lib(tmp_path, kiwix):
    r = Running(tmp_path, kiwix)
    yield r
    r.close()


def test_static_file_and_headers(lib):
    r, body = lib.get("/")
    assert r.status == 200 and b"Home" in body
    assert "default-src 'self'" in r.getheader("Content-Security-Policy")
    assert "object-src 'none'" in r.getheader("Content-Security-Policy")
    assert r.getheader("X-Content-Type-Options") == "nosniff"
    assert r.getheader("Referrer-Policy") == "no-referrer"
    assert r.getheader("Cache-Control") == "no-cache"
    assert lib.get("/app.js")[0].getheader("Content-Type").startswith("text/javascript")
    assert lib.get("/font.woff2")[0].getheader("Content-Type") == "font/woff2"
    r, body = lib.get("/", method="HEAD")
    assert r.status == 200 and body == b""
    assert lib.get("/missing.html")[0].status == 404


@pytest.mark.parametrize("path", ["/../private.txt", "/%2e%2e/private.txt", "/..%2fprivate.txt",
                                  "/%2e%2e%5cprivate.txt", "/C:/Windows/win.ini", "/static/../../private.txt"])
def test_traversal_blocked(lib, path):
    r, body = lib.get(path)
    assert r.status in (400, 404) and b"private" not in body


def test_bad_host_rejected(lib):
    assert lib.get("/", headers={"Host": "evil.example"})[0].status == 403
    assert lib.get("/api/status", headers={"Host": "evil.example:%d" % lib.port})[0].status == 403
    assert lib.get("/", headers={"Host": "localhost:%d" % lib.port})[0].status == 200
    assert lib.get("/", headers={"Host": "127.0.0.1"})[0].status == 200
    assert lib.get("/", headers={"Host": "localhost:1"})[0].status == 403


def test_kiwix_proxy_and_search(lib):
    r, body = lib.get("/kiwix/catalog/v2/entries?count=-1")
    assert r.status == 200 and b"zimgit-water_en_2024-08" in body
    assert r.getheader("Content-Security-Policy") is None
    r, body = lib.get("/kiwix/search?format=xml&pattern=water&books.name=zimgit-water_en_2024-08"
                      "&books.name=wikipedia_en_top_maxi_2026-09")
    assert r.status == 200 and body.count(b"<item>") >= 2
    r, body = lib.get("/kiwix/content/zimgit-water_en_2024-08/Boiling")
    assert r.status == 200 and b"boil it hard" in body
    assert lib.get("/kiwix/content/nope/x")[0].status == 404
    assert lib.get("/kiwix/viewer", method="HEAD")[0].status == 200
    assert json.loads(lib.get("/kiwix/suggest?content=zimgit-water_en_2024-08&term=boil")[1])


def test_status_shape(lib):
    (lib.cfg["content_dir"] / "a.zim").write_bytes(b"x" * 100)
    (lib.cfg["content_dir"] / "sub").mkdir()
    (lib.cfg["content_dir"] / "sub" / "b.zim").write_bytes(b"y" * 50)
    r, body = lib.get("/api/status")
    d = json.loads(body)
    assert d["books"] == 8 and d["kiwix"] is True
    assert d["ask"] == {"enabled": False, "model": ""}
    assert d["content_bytes"] == 150 and d["limit_gb"] == 500
    assert d["version"] == "0.1.0"


def test_manifest_have_flags(lib):
    (lib.cfg["content_dir"] / "zimgit-water_en_2024-08.zim").write_bytes(b"x")
    items = {i["id"]: i for i in json.loads(lib.get("/api/manifest")[1])["items"]}
    assert items["zimgit-water_en"]["have"] is True
    assert items["usda-2015_en"]["have"] is False


def test_ask_off_is_404(lib):
    r, body = lib.get("/ask/api/health")
    assert r.status == 404 and json.loads(body) == {"error": "Ask is turned off"}
    r, body = lib.get("/ask/api/ask", method="POST", body=b'{"q":"hi"}', headers={"Content-Type": "application/json"})
    assert r.status == 404 and json.loads(body)["error"] == "Ask is turned off"


def test_kiwix_down_gives_503_but_site_loads(tmp_path):
    r = Running(tmp_path, "http://127.0.0.1:%d" % free_port())
    try:
        resp, body = r.get("/kiwix/catalog/v2/entries?count=-1")
        assert resp.status == 503 and b"not running" in body
        status = json.loads(r.get("/api/status")[1])
        assert status["books"] == 0 and status["kiwix"] is False
        assert b"Home" in r.get("/")[1]
    finally:
        r.close()


def test_empty_kiwix_reports_zero_books(tmp_path):
    srv, base = fake_kiwix.start(empty=True)
    r = Running(tmp_path, base)
    try:
        d = json.loads(r.get("/api/status")[1])
        assert d["books"] == 0 and d["kiwix"] is True
    finally:
        r.close()
        srv.shutdown()


def test_binds_loopback_only(lib):
    assert lib.srv.server_address[0] == "127.0.0.1"
