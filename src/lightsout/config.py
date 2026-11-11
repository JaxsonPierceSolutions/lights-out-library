"""Settings: built-in defaults, then config.json in the repo root, then environment variables."""
import copy
import json
import os
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
DEFAULTS = {
    "port": 8600,
    "kiwix_port": 8601,
    "content_dir": "content",
    "files_dir": "files",
    "layers": [],
    "open_browser": True,
    "ask": {
        "enabled": False,
        "model": "",
        "embed_model": "nomic-embed-text",
        "ollama_url": "http://127.0.0.1:11434",
        "kiwix_urls": [],
    },
}


class ConfigError(ValueError):
    """A setting is wrong; the message is written for the person running the library."""


def _check_ask(ask):
    host = urllib.parse.urlparse(str(ask["ollama_url"])).hostname
    # Questions must never leave this computer, so only a local Ollama is allowed.
    if host not in LOCAL_HOSTS:
        raise ConfigError("ask.ollama_url must point at this computer (127.0.0.1 or localhost), "
                          "not %r. Questions are never sent to another machine." % (host or ask["ollama_url"]))
    for key in ("model", "embed_model"):
        if "deepseek" in str(ask[key]).lower():
            raise ConfigError("ask.%s is %r: DeepSeek models are not allowed here. "
                              "Pick another model, for example llama3.1:8b." % (key, ask[key]))


def _int(value, name):
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise ConfigError("%s must be a whole number, not %r." % (name, value))
    if not 1 <= port <= 65535:
        raise ConfigError("%s must be between 1 and 65535." % name)
    return port


def load_config(root=ROOT, env=None):
    env = os.environ if env is None else env
    root = Path(root)
    cfg = copy.deepcopy(DEFAULTS)
    path = root / "config.json"
    if path.is_file():
        try:
            user = json.loads(path.read_text(encoding="utf-8-sig"))
        except ValueError as e:
            raise ConfigError("config.json is not valid JSON (%s). Fix it or delete it to use the defaults." % e)
        if not isinstance(user, dict):
            raise ConfigError("config.json must contain a JSON object.")
        ask = user.pop("ask", {})
        if not isinstance(ask, dict):
            raise ConfigError("config.json: \"ask\" must be an object.")
        cfg.update(user)
        cfg["ask"].update(ask)
    if env.get("LIGHTSOUT_PORT"):
        cfg["port"] = env["LIGHTSOUT_PORT"]
    if env.get("LIGHTSOUT_KIWIX_PORT"):
        cfg["kiwix_port"] = env["LIGHTSOUT_KIWIX_PORT"]
    if env.get("LIGHTSOUT_CONTENT_DIR"):
        cfg["content_dir"] = env["LIGHTSOUT_CONTENT_DIR"]
    if env.get("LIGHTSOUT_NO_BROWSER") == "1":
        cfg["open_browser"] = False
    cfg["port"] = _int(cfg["port"], "port")
    cfg["kiwix_port"] = _int(cfg["kiwix_port"], "kiwix_port")
    cfg["content_dir"] = Path(root, cfg["content_dir"]).resolve()  # absolute second arg wins
    cfg["files_dir"] = Path(root, cfg["files_dir"]).resolve()
    if env.get("LIGHTSOUT_LAYERS"):
        cfg["layers"] = [x for x in env["LIGHTSOUT_LAYERS"].split(os.pathsep) if x]
    if not isinstance(cfg["layers"], list):
        raise ConfigError("\"layers\" must be a list of folders.")
    cfg["layers"] = [Path(root, x).resolve() for x in cfg["layers"]]
    cfg["kiwix_url"] = (env.get("LIGHTSOUT_KIWIX_URL") or "").rstrip("/") or None
    cfg["root"] = root
    cfg["ask"]["enabled"] = bool(cfg["ask"]["enabled"])
    _check_ask(cfg["ask"])
    return cfg


def kiwix_base(cfg):
    return cfg["kiwix_url"] or "http://127.0.0.1:%d" % cfg["kiwix_port"]


def find_zims(content_dir):
    """.zim files in the folder and one level of subfolders, sorted by name."""
    content_dir = Path(content_dir)
    if not content_dir.is_dir():
        return []
    found = list(content_dir.glob("*.zim")) + list(content_dir.glob("*/*.zim"))
    return sorted((p for p in found if p.is_file()), key=lambda p: p.name)
