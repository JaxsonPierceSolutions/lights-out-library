"""Add-on layers (docs/layers.md), the static build, Your own files, and Ask on its own."""
import http.client
import json
import threading

import pytest

import fake_kiwix
from helpers import make_cfg
from lightsout import ask, askserve, build, config, layers
from lightsout import server as srvmod


def make_layer(root, name="Our House", **extra):
    root.mkdir(parents=True, exist_ok=True)
    data = {"name": name, "lede": "Our house library.", "section": "This house",
            "cards": [{"title": "Inventory", "blurb": "Food and fuel", "href": "/inventory.html", "icon": "box"}],
            "footer": [{"text": "Printed sheet", "href": "/start-here.html"}],
            "replace": {"Runs on this computer only. Nothing leaves it.": "Runs in this house only."}}
    data.update(extra)
    (root / "layer.json").write_text(json.dumps(data), encoding="utf-8")
    (root / "site").mkdir(exist_ok=True)
    (root / "site" / "inventory.html").write_text("<title>Inventory · Lights Out Library</title><h1>Inventory</h1>", encoding="utf-8")
    return root


def get(port, path, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", path, headers=headers or {})
    r = c.getresponse()
    body = r.read()
    c.close()
    return r, body


@pytest.fixture()
def running(tmp_path):
    kiwix, kiwix_url = fake_kiwix.start()
    files = tmp_path / "files"
    (files / "music" / "Album").mkdir(parents=True)
    (files / "music" / "Album" / "song.mp3").write_bytes(b"0123456789")
    (files / ".hidden").mkdir()
    lay = make_layer(tmp_path / "household")
    cfg = make_cfg(tmp_path, kiwix_url=kiwix_url, layers=[lay], files_dir=files)
    srv = srvmod.make_server(cfg)
    threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()
    kiwix.shutdown()
    kiwix.server_close()


def test_layer_name_cards_and_words_reach_the_home_page(running):
    r, body = get(running, "/")
    html = body.decode()
    assert r.status == 200
    assert "<title>Our House</title>" in html
    assert '<h1 data-layer="name">Our House</h1>' in html
    assert "Our house library." in html
    assert 'href="/inventory.html"' in html and "<h2>This house</h2>" in html
    assert "Runs in this house only." in html and "Runs on this computer only" not in html
    assert '<a href="/start-here.html">Printed sheet</a>' in html
    assert 'id="files-card"' in html, "kept: the layer has no files card of its own"


def test_layer_pages_are_served_and_other_pages_get_the_name(running):
    r, body = get(running, "/inventory.html")
    assert r.status == 200 and b"<title>Inventory \xc2\xb7 Our House</title>" in body
    r, body = get(running, "/answers.html")
    assert r.status == 200 and "· Our House</title>".encode() in body
    r, body = get(running, "/api/layer")
    data = json.loads(body)
    assert data["name"] == "Our House" and "dirs" not in data, "folder paths never reach the browser"


def test_layer_cannot_reach_outside_its_site_folder(running, tmp_path):
    (tmp_path / "household" / "secret.txt").write_text("no")
    r, _ = get(running, "/../secret.txt")
    assert r.status == 404
    r, _ = get(running, "/%2e%2e/secret.txt")
    assert r.status == 404
    (tmp_path / "household" / "site" / ".env").write_text("SECRET=1")
    r, _ = get(running, "/.env")
    assert r.status == 404, "dotfiles in a layer are never served"


def test_files_are_listed_like_nginx_and_play_with_ranges(running):
    r, body = get(running, "/files/")
    top = json.loads(body)
    assert [i["name"] for i in top] == ["music"] and top[0]["type"] == "directory", "hidden folders stay hidden"
    r, body = get(running, "/files/music/Album/")
    assert json.loads(body)[0] == {**json.loads(body)[0], "name": "song.mp3", "type": "file", "size": 10}
    r, body = get(running, "/files/music/Album/song.mp3", {"Range": "bytes=2-5"})
    assert r.status == 206 and body == b"2345" and r.getheader("Content-Range") == "bytes 2-5/10"
    r, body = get(running, "/files/music/Album/song.mp3")
    assert r.status == 200 and body == b"0123456789"
    r, _ = get(running, "/files/../layer.json")
    assert r.status == 404
    r, _ = get(running, "/files/music")
    assert r.status == 301


def test_files_with_no_folder_is_an_empty_list(tmp_path):
    kiwix, kiwix_url = fake_kiwix.start()
    cfg = make_cfg(tmp_path, kiwix_url=kiwix_url)
    srv = srvmod.make_server(cfg)
    threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()
    r, body = get(srv.server_address[1], "/files/")
    assert r.status == 200 and json.loads(body) == []
    srv.shutdown()
    srv.server_close()
    kiwix.shutdown()
    kiwix.server_close()


def test_bad_layers_are_refused_with_a_plain_message(tmp_path):
    with pytest.raises(layers.LayerError, match="no layer.json"):
        layers.load([tmp_path])
    make_layer(tmp_path / "a", cards=[{"title": "x", "href": "javascript:alert(1)"}])
    with pytest.raises(layers.LayerError, match="run scripts"):
        layers.load([tmp_path / "a"])
    make_layer(tmp_path / "a2", cards=[{"title": "x", "href": "java\tscript:alert(1)"}])
    with pytest.raises(layers.LayerError, match="run scripts"):
        layers.load([tmp_path / "a2"])
    make_layer(tmp_path / "a3", footer=[{"text": "x", "href": "data:text/html,hi"}])
    with pytest.raises(layers.LayerError, match="run scripts"):
        layers.load([tmp_path / "a3"])
    make_layer(tmp_path / "b", scripts=["https://example.com/x.js"])
    with pytest.raises(layers.LayerError, match="paths on this site"):
        layers.load([tmp_path / "b"])
    make_layer(tmp_path / "c", cards=[{"title": "x", "href": "/", "icon": "rocket"}])
    with pytest.raises(layers.LayerError, match="unknown icon"):
        layers.load([tmp_path / "c"])


def test_layers_stack_in_order(tmp_path):
    a = make_layer(tmp_path / "a", name="First")
    b = make_layer(tmp_path / "b", name="Second", cards=[{"title": "Wake", "href": "/wake", "icon": "power", "id": "wake", "wide": True}])
    m = layers.load([a, b])
    assert m["name"] == "Second"
    assert [c["title"] for c in m["cards"]] == ["Inventory", "Wake"]
    assert m["layers"] == ["a", "b"]
    c = make_layer(tmp_path / "c", cards=[{"title": "Files elsewhere", "href": "/x", "id": "wake"}])
    assert [x["title"] for x in layers.load([a, b, c])["cards"]] == ["Inventory", "Files elsewhere"], "same id replaces in place"


def test_static_build_has_every_page_rendered_and_the_api_files(tmp_path):
    lay = make_layer(tmp_path / "household", scripts=["/layer/home.js"])
    r = build.build(tmp_path / "dist", [lay], ask_model="llama3.1:8b")
    out = r["out"]
    home = (out / "index.html").read_text(encoding="utf-8")
    assert "<title>Our House</title>" in home and 'href="/inventory.html"' in home
    assert home.rstrip().endswith('<script src="/layer/home.js"></script>\n</body>\n</html>')
    assert (out / "inventory.html").is_file() and (out / "files.html").is_file()
    assert "· Our House</title>" in (out / "search.html").read_text(encoding="utf-8")
    status = json.loads((out / "api" / "status").read_text())
    assert status["ask"] == {"enabled": True, "model": "llama3.1:8b"} and status["static"]
    assert json.loads((out / "api" / "manifest").read_text())["items"]
    assert json.loads((out / "api" / "layer").read_text())["name"] == "Our House"
    assert not (out / "layer.json").exists()


def test_a_layer_files_card_replaces_the_built_in_one(tmp_path):
    lay = make_layer(tmp_path / "h", cards=[{"title": "Music", "href": "/files.html?dir=music", "icon": "music"}])
    home = (build.build(tmp_path / "dist", [lay])["out"] / "index.html").read_text(encoding="utf-8")
    assert 'id="files-card"' not in home and "ownFiles()" in home


def test_build_never_wipes_a_folder_it_did_not_make(tmp_path):
    (tmp_path / "mine").mkdir()
    (tmp_path / "mine" / "notes.txt").write_text("keep")
    with pytest.raises(SystemExit):
        build.build(tmp_path / "mine")
    assert (tmp_path / "mine" / "notes.txt").read_text() == "keep"
    build.build(tmp_path / "dist")
    build.build(tmp_path / "dist")  # building again into its own folder is fine


def test_build_without_layers_is_the_plain_library(tmp_path):
    out = build.build(tmp_path / "dist")["out"]
    home = (out / "index.html").read_text(encoding="utf-8")
    assert "<title>Lights Out Library</title>" in home and "<!--layer:cards-->" in home
    assert json.loads((out / "api" / "status").read_text())["ask"]["enabled"] is False


def test_ask_uses_the_first_book_server_that_answers(tmp_path):
    kiwix, kiwix_url = fake_kiwix.start()
    cfg = make_cfg(tmp_path, ask={"enabled": True, "model": "m", "kiwix_urls": ["http://127.0.0.1:9", kiwix_url]})
    ask.configure(cfg)
    try:
        assert ask.kiwix() == kiwix_url.rstrip("/")
        kiwix.shutdown()
        kiwix.server_close()
        ask._kiwix["at"] = 0  # force the 30-second recheck now
        with pytest.raises(ask.AskError, match="not answering"):
            ask.kiwix()
    finally:
        ask.configure(make_cfg(tmp_path))


def test_askserve_answers_health_on_both_paths(tmp_path):
    kiwix, kiwix_url = fake_kiwix.start()
    cfg = make_cfg(tmp_path, kiwix_url=kiwix_url, ask={"enabled": True, "model": "m"})
    srv = askserve.make_server(cfg, 0)
    assert srv.server_address[0] == "127.0.0.1"
    threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()
    port = srv.server_address[1]
    for path in ("/health", "/ask/api/health"):
        r, body = get(port, path)
        st = json.loads(body)
        assert r.status == 200 and st["model"] == "m" and st["library_books"] >= 1, path
    r, _ = get(port, "/nope")
    assert r.status == 404
    srv.shutdown()
    srv.server_close()
    kiwix.shutdown()
    kiwix.server_close()
    ask.configure(make_cfg(tmp_path))


def test_layers_setting_in_config_is_relative_to_the_project(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"layers": ["../household"]}))
    cfg = config.load_config(root=tmp_path, env={})
    assert cfg["layers"] == [(tmp_path / ".." / "household").resolve()]
    with pytest.raises(config.ConfigError):
        (tmp_path / "config.json").write_text(json.dumps({"layers": "x"}))
        config.load_config(root=tmp_path, env={})
