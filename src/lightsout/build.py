"""Build the library pages as plain files, for a web server such as nginx to serve.

    python -m lightsout.build --out dist [--layer DIR ...] [--ask-model NAME]

The result is the library's site/ with any layers on top (see docs/layers.md), every page
already rendered with the layers' name, cards and word changes, plus three small JSON files the
pages read: api/manifest, api/status and api/layer. The web server must:

  * serve the folder as static files, with api/* as application/json;
  * pass /kiwix/ to kiwix-serve started with --urlRootLocation /kiwix;
  * optionally pass /ask/api/ to ``python -m lightsout.askserve`` and serve /files/ as a
    JSON folder listing (nginx: autoindex on; autoindex_format json).

deploy/nginx.example.conf shows all of it. The local server (start.cmd / start.sh) needs none
of this; it does the same thing as it goes.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__, config, layers

SITE_DIR = config.ROOT / "site"
MANIFEST = config.ROOT / "manifest" / "content.json"


def build(out, layer_dirs=(), ask_model="", site_dir=SITE_DIR, manifest_path=MANIFEST):
    out = Path(out).resolve()
    site_dir = Path(site_dir).resolve()
    layer = layers.load(layer_dirs)
    if out == site_dir or site_dir in out.parents:
        raise SystemExit("Build into a folder outside site/.")
    marker = out / ".lightsout-build"
    if out.exists() and any(out.iterdir()) and not marker.is_file():
        raise SystemExit("%s already has files that this build didn't make. Pick an empty folder." % out)
    # Nothing is deleted: a folder from an earlier build is written over in place.
    shutil.copytree(site_dir, out, dirs_exist_ok=True)
    marker.write_text("Made by python -m lightsout.build. Safe to build into again.\n", encoding="utf-8")
    for d in layer["dirs"]:
        if (d / "site").is_dir():
            shutil.copytree(d / "site", out, dirs_exist_ok=True)
    pages = 0
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        page.write_text(layers.render(text, layer, page.name if page.parent == out else ""), encoding="utf-8")
        pages += 1
    api = out / "api"
    api.mkdir(exist_ok=True)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    (api / "manifest").write_text(json.dumps(manifest), encoding="utf-8")
    status = {"version": __version__, "static": True, "books": 0, "kiwix": True,
              "ask": {"enabled": bool(ask_model), "model": ask_model},
              "limit_gb": manifest.get("limit_gb", 500), "layers": layer["layers"]}
    (api / "status").write_text(json.dumps(status), encoding="utf-8")
    (api / "layer").write_text(json.dumps(layers.public(layer)), encoding="utf-8")
    return {"out": out, "pages": pages, "layers": layer["layers"]}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lightsout.build", description="Build the library pages as static files.")
    ap.add_argument("--out", required=True, help="empty folder, or one an earlier build made (written over in place)")
    ap.add_argument("--layer", action="append", default=[], metavar="DIR", help="add-on layer; repeat to stack")
    ap.add_argument("--ask-model", default="", help="show Ask, naming this model (Ask runs separately, see askserve)")
    args = ap.parse_args(argv)
    try:
        r = build(args.out, args.layer, args.ask_model)
    except layers.LayerError as e:
        print("Layer problem: %s" % e)
        return 1
    print("Built %d pages into %s%s." % (r["pages"], r["out"], (" with layers: " + ", ".join(r["layers"])) if r["layers"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
