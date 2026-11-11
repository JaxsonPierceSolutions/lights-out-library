import http.client
import json
import threading

import pytest

import fake_kiwix
import fake_ollama
from helpers import make_cfg
from lightsout import ask, config
from lightsout import server as srvmod


@pytest.fixture
def stack(tmp_path):
    ksrv, kbase = fake_kiwix.start()
    requests = []
    osrv, obase = fake_ollama.start(requests)
    cfg = make_cfg(tmp_path, kiwix_url=kbase, ask={"enabled": True, "model": "testmodel:1b", "ollama_url": obase})
    site = tmp_path / "site"
    site.mkdir()
    srv = srvmod.make_server(cfg, site)
    threading.Thread(target=srv.serve_forever, args=(0.05,), daemon=True).start()

    class S:
        port = srv.server_address[1]
        reqs = requests
        config = cfg

        def post(self, body):
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
            c.request("POST", "/ask/api/ask", json.dumps(body), {"Content-Type": "application/json"})
            r = c.getresponse()
            data = r.read().decode()
            c.close()
            return r, data

        def get(self, path):
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
            c.request("GET", path)
            r = c.getresponse()
            return r, json.loads(r.read())
    yield S()
    srv.shutdown()
    srv.server_close()
    ksrv.shutdown()
    osrv.shutdown()


def test_question_returns_sources_then_text(stack):
    r, data = stack.post({"q": "How do I make water safe to drink?"})
    assert r.status == 200
    first, _, answer = data.partition("\n")
    head = json.loads(first)
    assert head["queries"][0] == "purify water"
    assert head["sources"] and all({"n", "title", "book", "link"} <= set(s) for s in head["sources"])
    assert any("zimgit-water" in s["link"] for s in head["sources"])
    assert answer == "".join(fake_ollama.ANSWER)
    gen = [b for p, b in stack.reqs if p == "/api/generate" and b["stream"]][0]
    assert gen["model"] == "testmodel:1b" and gen["options"]["temperature"] == 0 and "seed" in gen["options"]
    assert len({p for p in [gen["prompt"].count("\n[%d] " % n) for n in range(1, 9)]}) >= 1
    embeds = [b for p, b in stack.reqs if p == "/api/embed"]
    assert embeds and embeds[0]["model"] == "nomic-embed-text"


def test_notes_go_first(stack):
    note = {"title": "Boil water", "text": "Boil water hard for one full minute before drinking it, longer at altitude."}
    r, data = stack.post({"q": "make water safe to drink", "notes": [note]})
    head = json.loads(data.split("\n", 1)[0])
    assert head["sources"][0]["title"] == "Boil water" and head["sources"][0]["n"] == 1
    gen = [b for p, b in stack.reqs if p == "/api/generate" and b["stream"]][0]
    prompt = gen["prompt"]
    assert prompt.index("[1] (Checked quick answer: Boil water)") < prompt.index("[2]")
    assert "Household" not in gen["system"] + prompt


def test_at_most_eight_passages(stack):
    stack.post({"q": "water"})
    gen = [b for p, b in stack.reqs if p == "/api/generate" and b["stream"]][0]
    assert gen["prompt"].count("\n[") <= 9  # 8 passages; the first one follows a blank line


def test_empty_question_and_health(stack):
    r, data = stack.post({"q": "  "})
    assert r.status == 400 and "error" in json.loads(data)
    r, h = stack.get("/ask/api/health")
    assert r.status == 200 and h["ok"] is True and h["model"] == "testmodel:1b" and h["library_books"] == 8


def test_no_model_says_what_to_set(stack):
    ask.configure({**stack.config, "ask": {**stack.config["ask"], "model": ""}})
    r, data = stack.post({"q": "water"})
    assert r.status == 400 and "ask.model" in json.loads(data)["error"] and "config.json" in json.loads(data)["error"]


def test_book_patterns_match_manifest_ids():
    ids = [i["id"] for i in json.load(open(config.ROOT / "manifest" / "content.json", encoding="utf-8"))["items"]]
    medical = {i for i in ids if ask.MEDICAL_BOOKS.search(i)}
    assert {"wikipedia_en_medicine_maxi", "mdwiki_en_all_maxi", "nhs.uk_en_medicines", "zimgit-medicine_en",
            "irp.fas.org_en_military-medicine", "quickguidesformedicine_en_all"} == medical
    archive = {i for i in ids if ask.ARCHIVE.search(i)}
    assert {"wikipedia_en_all_nopic", "wikipedia_en_all_maxi", "gutenberg_en_lcc-s", "gutenberg_en_lcc-t", "survivorlibrary.com_en_all"} == archive
    assert {i for i in ids if ask.VIDEO_BOOKS.search(i)} >= {"lrnselfreliance_en_all", "urban-prepper_en_all", "canadian-prepper_en_preppingfood"}
    assert {i for i in ids if ask.VET_BOOKS.search(i)} == {"wikivet.net_en_all_maxi", "pets.stackexchange.com_en_all"}


def test_medical_question_reads_only_medical_books(stack, monkeypatch):
    calls = []
    real = ask.search
    monkeypatch.setattr(ask, "search", lambda base, q, pool, n=10: (calls.append(list(pool)), real(base, q, pool, n))[1])
    monkeypatch.setattr(ask, "plan", lambda q: (["wound care"], True))
    _, sources, _ = ask.retrieve("how do I clean a cut", None)
    assert calls and all(ask.MEDICAL_BOOKS.search(b) for pool in calls for b in pool)
    assert sources and all("wikipedia_en_medicine" in s["link"] for s in sources)


def test_deepseek_model_refused(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"ask": {"enabled": True, "model": "DeepSeek-R1:8b"}}))
    with pytest.raises(config.ConfigError, match="DeepSeek"):
        config.load_config(root=tmp_path, env={})


def test_non_local_ollama_refused(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"ask": {"ollama_url": "http://192.0.2.5:11434"}}))
    with pytest.raises(config.ConfigError, match="this computer"):
        config.load_config(root=tmp_path, env={})
    for ok in ("http://localhost:11434", "http://127.0.0.1:1", "http://[::1]:11434"):
        (tmp_path / "config.json").write_text(json.dumps({"ask": {"ollama_url": ok}}))
        assert config.load_config(root=tmp_path, env={})["ask"]["ollama_url"] == ok
