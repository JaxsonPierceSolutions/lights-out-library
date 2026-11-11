"""A tiny stand-in for kiwix-serve, with made-up books. Not a real Kiwix; just enough for tests.

As a script:  python tests/fake_kiwix.py --port 8601 [--empty]
As a fixture: from fake_kiwix import start; srv, base = start()
"""
import argparse
import html
import json
import os
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOREM = "This made-up page is test data for the library and is not taken from any real book. "


def page(path, title, *paras):
    return {"path": path, "title": title, "paras": [p + " " + LOREM for p in paras]}


BOOKS = [
    {"id": "wikipedia_en_medicine_maxi_2026-10", "title": "Medical encyclopedia (test)", "lang": "eng", "pages": [
        page("Wound_care", "Wound care", "Clean a small cut with clean water and cover it with a clean dry cloth, then change the cloth each day.",
             "Press firmly on a bleeding wound for ten minutes without lifting to check it."),
        page("Burns", "Burns", "Cool a minor burn under running water for twenty minutes, then cover it loosely.")]},
    {"id": "zimgit-water_en_2024-08", "title": "Water treatment guides (test)", "lang": "eng", "pages": [
        page("Boiling", "Boiling water", "Bring cloudy water through a cloth first, then boil it hard for one minute so it is safe to drink.",
             "Let boiled water cool in a covered clean container and store it away from the stove."),
        page("Storage", "Water storage", "Store drinking water in clean containers with tight lids, and keep them in a cool dark place.")]},
    {"id": "ifixit_en_all_2025-12", "title": "Repair guides (test)", "lang": "eng", "pages": [
        page("Leaky_tap", "Fix a leaking tap", "Turn off the water supply under the sink, then remove the handle and replace the worn washer inside.")]},
    {"id": "armypubs_en_all_2024-12", "title": "Field manuals (test)", "lang": "eng", "pages": [
        page("Shelter", "Building a shelter", "Choose a spot out of the wind and away from dead branches, and lay insulation under you before sleeping.")]},
    {"id": "gutenberg_en_lcc-t_2026-03", "title": "Old how-to books (test)", "lang": "eng", "pages": [
        page("Candles", "Making candles", "Old books describe dipping a wick in melted fat many times to build up a candle by hand.")]},
    {"id": "wikipedia_en_top_maxi_2026-09", "title": "Encyclopedia essentials (test)", "lang": "eng", "pages": [
        page("Water", "Water", "Water is a clear liquid that people need every day, and drinking water should be clean before it is used.")]},
    {"id": "wikipedia_en_all_nopic_2026-06", "title": "Every article (test)", "lang": "eng", "pages": [
        page("Water_(molecule)", "Water (molecule)", "A water molecule has two hydrogen atoms and one oxygen atom bonded together.")]},
    {"id": "cooking.stackexchange.com_en_all_2026-10", "title": "Cooking questions (test)", "lang": "eng", "pages": [
        page("questions/1/rice-storage", "How long does cooked rice keep?", "Cooked rice should be cooled quickly and eaten within a day, because it spoils faster than most people expect.")]},
]


def make_handler(books):
    by_id = {b["id"]: b for b in books}

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def reply(self, code, body, ctype):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            u = urllib.parse.urlsplit(self.path)
            q = urllib.parse.parse_qs(u.query)
            if not u.path.startswith("/kiwix"):
                return self.reply(404, "not found", "text/plain")
            path = u.path[len("/kiwix"):] or "/"
            if path == "/catalog/v2/entries":
                return self.catalog(q)
            if path == "/search":
                return self.search(q)
            if path == "/suggest":
                return self.suggest(q)
            if path == "/viewer":
                return self.reply(200, "<!doctype html><title>Viewer</title><p>Fake viewer</p>", "text/html; charset=utf-8")
            if path.startswith("/content/"):
                return self.content(path[len("/content/"):])
            self.reply(404, "not found", "text/plain")

        def catalog(self, q):
            count = int((q.get("count") or ["-1"])[0])
            shown = books if count < 0 else books[:count]
            entries = "".join(
                "<entry><title>%s</title><name>%s</name><language>%s</language><summary>%s</summary>"
                '<link rel="alternate" type="text/html" href="/kiwix/content/%s"/>'
                '<link rel="http://opds-spec.org/acquisition/open-access" type="application/x-zim" href="/kiwix/catalog/v2/illustration/%s" length="%d"/></entry>'
                % (html.escape(b["title"]), b["id"], b["lang"], html.escape(b["title"]), b["id"], b["id"], 1000 + len(b["id"]))
                for b in shown)
            xml = ('<?xml version="1.0" encoding="UTF-8"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
                   "<title>Fake catalog</title><totalResults>%d</totalResults><startIndex>0</startIndex><itemsPerPage>%d</itemsPerPage>%s</feed>"
                   % (len(books), len(shown), entries))
            self.reply(200, xml, "application/atom+xml;profile=opds-catalog;kind=acquisition; charset=utf-8")

        def search(self, q):
            names = q.get("books.name") or [b["id"] for b in books]
            chosen = [by_id[n] for n in names if n in by_id]
            if len({b["lang"] for b in chosen}) > 1:
                return self.reply(400, "Selected books have different languages", "text/plain")
            words = [w for w in re.findall(r"[a-z0-9]+", (q.get("pattern") or [""])[0].lower()) if len(w) > 2]
            items = []
            for b in chosen:
                for p in b["pages"]:
                    text = (p["title"] + " " + " ".join(p["paras"])).lower()
                    hits = [w for w in words if w in text]
                    if hits:
                        snippet = html.escape(p["paras"][0][:120])
                        marks = "|".join(re.escape(w) for w in hits)
                        snippet = re.sub("(?i)(%s)" % marks, lambda m: "<b>" + m.group(0) + "</b>", snippet)
                        items.append((len(hits), "<item><title>%s</title><link>/kiwix/content/%s/%s</link>"
                                      "<description>%s</description><book><title>%s</title></book><wordCount>%d</wordCount></item>"
                                      % (html.escape(p["title"]), b["id"], p["path"], snippet,
                                         html.escape(b["title"]), len(text.split()))))
            items.sort(key=lambda t: -t[0])
            body = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Search</title>'
                    "<totalResults>%d</totalResults>%s</channel></rss>" % (len(items), "".join(i for _, i in items)))
            self.reply(200, body, "application/rss+xml; charset=utf-8")

        def suggest(self, q):
            term = (q.get("term") or [""])[0].lower()
            out = [{"value": p["title"], "label": p["title"], "kind": "path", "path": p["path"]}
                   for b in books if b["id"] in (q.get("content") or [b["id"]])
                   for p in b["pages"] if term and term in p["title"].lower()]
            self.reply(200, json.dumps(out), "application/json; charset=utf-8")

        def content(self, rest):
            book_id, _, path = urllib.parse.unquote(rest).partition("/")
            b = by_id.get(book_id)
            if not b:
                return self.reply(404, "no such book", "text/plain")
            if not path:
                path = b["pages"][0]["path"]
            for p in b["pages"]:
                if p["path"] == path:
                    body = "<!doctype html><html><head><title>%s</title></head><body><h1>%s</h1>%s</body></html>" % (
                        html.escape(p["title"]), html.escape(p["title"]), "".join("<p>%s</p>" % html.escape(x) for x in p["paras"]))
                    return self.reply(200, body, "text/html; charset=utf-8")
            self.reply(404, "no such page", "text/plain")

    return H


def start(port=0, empty=None):
    if empty is None:
        empty = os.environ.get("FAKE_KIWIX_EMPTY") == "1"
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler([] if empty else BOOKS))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8601)
    ap.add_argument("--empty", action="store_true")
    a = ap.parse_args()
    s, base = start(a.port, a.empty)
    print("fake kiwix on", base, flush=True)
    threading.Event().wait()
