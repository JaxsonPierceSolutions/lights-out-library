"""Ask: answer a plain-English question from the offline library, using a local AI model.

For each question:
  1. the local model turns the question into search terms,
  2. Kiwix is searched, book by book,
  3. the best pages are fetched, cut into passages and ranked by embedding similarity,
  4. the model answers from those passages only, citing them.
Nothing here touches the internet: Kiwix and Ollama are both on this computer.

POST body {"q": "...", "notes": [{"title","text"}]} -> first line JSON {"sources": [...], "queries": [...]}
                                                       then the answer as streamed plain text.
"""
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from . import config

NUM_CTX = 4096

ARCHIVE = re.compile(r"wikipedia_en_all_|gutenberg|survivorlibrary")
# No forum threads in the medical pool: they mix advice meant for different places.
MEDICAL_BOOKS = re.compile(r"wikipedia_en_medicine|mdwiki|quickguides|nhs\.uk|military-medicine|zimgit-medicine")
VIDEO_BOOKS = re.compile(r"prepper_en|lrnselfreliance|urban-prepper")  # video pages have little text
VET_BOOKS = re.compile(r"wikivet|pets\.")
ANIMAL = re.compile(r"\b(dog|cat|cow|cattle|horse|chicken|hen|goat|pig|hog|sheep|rabbit|livestock|pet|pets|animal|animals|puppy|kitten|calf|duck)s?\b", re.I)
REFERENCE = re.compile(r"mdwiki|wikipedia_en|nhs\.uk|quickguides|ready\.gov|armypubs|military|zimgit|usda|appropedia|cd3wd|wikibooks|ifixit|trueprepper|scoutwiki|energypedia|gardenology|libretexts")
JUNK = re.compile(r"^questions/tagged/|_page=\d+$|^(highest voted|newest|hot|active) .* questions$|/[a-z]{2}(-[a-z]+)?$|^(category|template|user|file|talk):|editing instructions$", re.I)
STOPWORDS = set("how what when where why which who the and for with from that this are was can you your our does not into about should would could will have has had them they their there here than then also".split())

_cfg = None
_catalog = {}  # kiwix base -> {"at": time, "books": [...]}
_kiwix = {"base": None, "at": 0}  # the book server in use, and when it was last checked


class AskError(Exception):
    """Something the person can fix or wait out; the message is shown to them."""


def configure(cfg):
    global _cfg
    _cfg = cfg
    _catalog.clear()
    _kiwix.update(base=None, at=0)


def _settings():
    if _cfg is None:
        raise AskError("Ask is not set up.")
    a = _cfg["ask"]
    if not a["model"]:
        raise AskError("Ask has no AI model chosen yet. Set ask.model (for example \"llama3.1:8b\") in config.json "
                       "and set ask.enabled to true, then restart the library.")
    return a


def http(url, data=None, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    return urllib.request.urlopen(req, timeout=timeout)


def kiwix():
    """The first book server that answers. ask.kiwix_urls can list several (for example one on this
    computer and a bigger one elsewhere in the house); the choice is rechecked every 30 seconds."""
    sources = [str(u).rstrip("/") for u in (_cfg["ask"].get("kiwix_urls") or [])] or [config.kiwix_base(_cfg)]
    if _kiwix["base"] in sources and time.time() - _kiwix["at"] < 30:
        return _kiwix["base"]
    for base in sources:
        try:
            http(base + "/kiwix/catalog/v2/entries?count=1", timeout=3).read()
        except Exception:
            continue
        if base != _kiwix["base"] and len(sources) > 1:
            sys.stderr.write("%s using the book server at %s\n" % (time.strftime("%F %T"), base))
        _kiwix.update(base=base, at=time.time())
        return base
    _kiwix.update(base=None, at=0)
    raise AskError("The book server is not answering.")


def books(base):
    c = _catalog.setdefault(base, {"at": 0, "books": []})
    if time.time() - c["at"] > 600 or not c["books"]:
        xml = http(base + "/kiwix/catalog/v2/entries?count=-1", timeout=20).read().decode("utf-8", "ignore")
        c["books"] = sorted(set(re.findall(r'href="/kiwix/content/([^"/]+)', xml)))
        c["at"] = time.time()
    return c["books"]


def generate(prompt, system=None, num_predict=200, temperature=0.2, fmt=None):
    a = _settings()
    body = {"model": a["model"], "prompt": prompt, "stream": False, "keep_alive": "30m",
            "options": {"num_predict": num_predict, "temperature": temperature, "num_ctx": NUM_CTX}}
    if system:
        body["system"] = system
    if fmt:
        body["format"] = fmt
    return json.load(http(a["ollama_url"] + "/api/generate", body, timeout=180))["response"]


def embed(texts):
    a = _settings()
    out = []
    for i in range(0, len(texts), 32):
        r = json.load(http(a["ollama_url"] + "/api/embed",
                           {"model": a["embed_model"], "input": texts[i:i + 32], "keep_alive": "30m"}, timeout=180))
        out.extend(r["embeddings"])
    return out


def cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0


def plan(question):
    """Ask the model for search terms and whether the question is medical."""
    prompt = (
        "A person is searching an offline reference library (encyclopedia, medical references, repair guides, "
        "survival and farming manuals, Q&A archives). Turn their question into search terms.\n"
        "Return JSON: {\"queries\": [two or three short keyword searches, 2-4 words each, using the technical or "
        "encyclopedia terms an article title would use], \"medical\": true or false}.\n"
        "Example: question \"how do I treat a deep cut\" -> {\"queries\": [\"laceration wound care\", \"wound closure first aid\", \"wound\"], \"medical\": true}\n"
        "Example: question \"how long is canned food good for\" -> {\"queries\": [\"canned food shelf life\", \"canning food storage\"], \"medical\": false}\n"
        f"Question: {question}\nJSON:")
    try:
        d = json.loads(generate(prompt, num_predict=120, temperature=0.0, fmt="json"))
        qs = [q.strip() for q in d.get("queries", []) if isinstance(q, str) and q.strip()][:3]
        med = bool(d.get("medical"))
    except Exception:
        qs, med = [], False
    stop = set("how what when where why which who is are was do does did i you we my our the a an to of for in on at it be should would could will can good long much many best way with and or if from".split())
    plain = " ".join(w for w in re.sub(r"[^a-z0-9\s'-]", " ", question.lower()).split() if w not in stop)
    if plain and plain not in qs:
        qs.append(plain)
    return qs or [question], med


def search(base, query, book_ids, n=10):
    # Kiwix refuses (HTTP 400) a search across books of different languages, so pools are English only.
    url = (base + "/kiwix/search?format=xml&pageLength=40&start=1&pattern=" + urllib.parse.quote(query)
           + "".join("&books.name=" + urllib.parse.quote(b) for b in book_ids))
    try:
        root = ET.fromstring(http(url, timeout=60).read())
    except Exception:
        return []
    out, per_book = [], {}
    for it in root.iter("item"):
        title = it.findtext("title") or ""
        link = (it.findtext("link") or "").split("/content/", 1)[-1]
        book = link.split("/")[0]
        if JUNK.search(title) or per_book.get(book, 0) >= 3:
            continue
        per_book[book] = per_book.get(book, 0) + 1
        out.append({"title": title, "link": link, "book": book, "bookTitle": it.findtext("book/title") or ""})
        if len(out) >= n:
            break
    return out


class Text(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "noscript", "sup", "table", "figure", "form"}
    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "div", "br", "tr", "dd", "dt", "blockquote", "pre"}

    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def page_text(base, link):
    try:
        raw = http(base + "/kiwix/content/" + urllib.parse.quote(link, safe="/"), timeout=30).read(600000)
    except Exception:
        return ""
    p = Text()
    try:
        p.feed(raw.decode("utf-8", "ignore"))
    except Exception:
        return ""
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in "".join(p.parts).split("\n")]
    return "\n".join(ln for ln in lines if len(ln) > 40)


def chunks(text, size=650):
    out, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) > size and cur:
            out.append(cur.strip())
            cur = ""
        while len(para) > size * 1.5:
            out.append(para[:size])
            para = para[size:]
        cur += para + " "
    if cur.strip():
        out.append(cur.strip())
    return out[:18]


SYSTEM = (
    "You are the library assistant for someone without power or internet. "
    "Answer the question for a person (not an animal, unless they ask about one) using ONLY the numbered excerpts. "
    "Write at most 120 words: first the direct answer in one or two plain sentences, then up to five short bullet points with the key steps or facts. "
    "Put the excerpt number in square brackets after each point, like [1]. "
    "If an excerpt is a 'Checked quick answer', trust it above the others and lead with it. "
    "Ignore excerpts that are off-topic. Say each thing once. Use everyday words. "
    "Emergency services may be out of reach: if the excerpts say to call for help, say so in a few words, but spend the answer on what the person can do themselves. "
    "Never invent a dose, quantity, temperature or time: use only numbers that appear in the excerpts. "
    "If excerpts disagree with each other, say that they disagree instead of picking one. "
    "Only when you could not answer at all, reply with just this: say exactly: \"The pages I found don't answer this.\" and then say in one sentence what they do cover."
)


def answer_stream(question, passages):
    a = _settings()
    ctx = "\n\n".join(f"[{p['n']}] ({p['title']})\n{p['text']}" for p in passages)
    prompt = f"Excerpts from the library:\n\n{ctx}\n\nQuestion: {question}\n\nAnswer:"
    body = {"model": a["model"], "system": SYSTEM, "prompt": prompt, "stream": True, "keep_alive": "30m",
            "options": {"num_predict": 260, "temperature": 0.0, "seed": 7, "num_ctx": NUM_CTX, "repeat_penalty": 1.15}}
    with http(a["ollama_url"] + "/api/generate", body, timeout=300) as r:
        for line in r:
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("response"):
                yield d["response"]
            if d.get("done"):
                break


def retrieve(question, notes=None):
    base = kiwix()
    queries, medical = plan(question)
    all_books = books(base)
    animal = bool(ANIMAL.search(question))
    core = [b for b in all_books if not ARCHIVE.search(b) and not VIDEO_BOOKS.search(b) and (animal or not VET_BOOKS.search(b))]
    med = [b for b in all_books if MEDICAL_BOOKS.search(b)]
    ref = [b for b in core if REFERENCE.search(b)]
    hits, seen = [], set()
    for q in queries:
        pools = [(med, 4)] if medical else [(ref, 3), (core, 2)]
        for pool, n in pools:
            if not pool:
                continue
            for h in search(base, q, pool, n):
                if h["link"] not in seen:
                    seen.add(h["link"])
                    hits.append(h)
    hits = hits[:9]
    cand = []
    for h in hits:
        for c in chunks(page_text(base, h["link"])):
            cand.append((h, c))
    # Embedding can be slow on a CPU, so first keep only the passages that share words with the question.
    terms = set(w for w in re.findall(r"[a-z]{3,}", (question + " " + " ".join(queries)).lower()) if w not in STOPWORDS)
    if len(cand) > 45 and terms:
        cand.sort(key=lambda hc: -sum(1 for w in terms if w in hc[1].lower()))
        cand = cand[:45]
    passages, sources, total = [], [], 0
    # Hand-checked quick answers go in first, as the lowest-numbered excerpts.
    for note in (notes or [])[:2]:
        sources.append({"n": len(sources) + 1, "title": note["title"], "book": "Quick answer (checked)", "link": ""})
        passages.append({"n": len(sources), "title": "Checked quick answer: " + note["title"], "text": note["text"][:1500]})
        total += len(passages[-1]["text"])
    if cand:
        vecs = embed(["search_query: " + question] + ["search_document: " + h["title"] + ". " + c for h, c in cand])
        qv = vecs[0]
        scored = sorted(((cos(qv, v), h, c) for v, (h, c) in zip(vecs[1:], cand)), key=lambda t: -t[0])
        per_page = {}
        for score, h, c in scored:
            if per_page.get(h["link"], 0) >= 2 or total + len(c) > 5200:
                continue
            per_page[h["link"]] = per_page.get(h["link"], 0) + 1
            if h["link"] not in [x["link"] for x in sources]:
                sources.append({"n": len(sources) + 1, "title": h["title"], "book": h["bookTitle"], "link": h["link"]})
            n = next(x["n"] for x in sources if x["link"] == h["link"])
            passages.append({"n": n, "title": h["title"], "text": c})
            total += len(c)
            if len(passages) >= 8:
                break
    passages.sort(key=lambda p: p["n"])
    return queries, sources, passages


def health():
    st = {"enabled": True}
    try:
        a = _settings()
        st["model"] = a["model"]
    except AskError as e:
        return {"enabled": True, "ok": False, "error": str(e)}
    try:
        base = kiwix()
        st["library_books"] = len(books(base))
        urls = [str(u).rstrip("/") for u in (_cfg["ask"].get("kiwix_urls") or [])]
        if len(urls) > 1:
            st["book_server"] = urls.index(base) + 1  # which one in the list, not its address
    except Exception as e:
        st["library_error"] = str(e)[:80]
    try:
        st["ollama"] = [m["name"] for m in json.load(http(a["ollama_url"] + "/api/tags", timeout=5))["models"]]
    except Exception as e:
        st["ollama_error"] = "Ollama is not answering. Start it, then try again. (%s)" % str(e)[:60]
    st["ok"] = "library_error" not in st and "ollama_error" not in st
    return st


def _send_json(handler, code, obj):
    body = json.dumps(obj).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def handle_ask(handler, body_bytes):
    try:
        _settings()
    except AskError as e:
        return _send_json(handler, 400, {"error": str(e)})
    try:
        body = json.loads(body_bytes or b"{}")
        q = (body.get("q") or "").strip()[:400]
        notes = [{"title": str(x.get("title", ""))[:200], "text": str(x.get("text", ""))[:1500]}
                 for x in (body.get("notes") or []) if isinstance(x, dict)]
    except Exception:
        q, notes = "", []
    if not q:
        return _send_json(handler, 400, {"error": "Type a question first."})
    t0 = time.time()
    try:
        queries, sources, passages = retrieve(q, notes)
    except AskError as e:
        return _send_json(handler, 502, {"error": str(e)})
    except Exception as e:
        sys.stderr.write("retrieve failed: %r\n" % (e,))
        return _send_json(handler, 502, {"error": "The library or the AI model is not answering. "
                                                  "Check that Ollama is running, then try again."})
    handler.close_connection = True  # streamed body has no length, so end it by closing
    handler.send_response(200)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Accel-Buffering", "no")  # so a proxy in front passes the answer on as it is written
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write((json.dumps({"sources": sources, "queries": queries}) + "\n").encode())
    handler.wfile.flush()
    if not passages:
        handler.wfile.write("I couldn't find pages about that in the library. Try the search box with different words.".encode())
        return
    try:
        for piece in answer_stream(q, passages):
            handler.wfile.write(piece.encode())
            handler.wfile.flush()
    except OSError:
        return  # the reader went away
    except Exception as e:
        sys.stderr.write("answer failed: %r\n" % (e,))
        try:
            handler.wfile.write("\n\n(The AI stopped before finishing.)".encode())
        except OSError:
            pass
    sys.stderr.write("answered %r in %.1fs with %d sources\n" % (q[:60], time.time() - t0, len(sources)))
