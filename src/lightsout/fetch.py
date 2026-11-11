"""Download books (and the Kiwix book server) from download.kiwix.org.

    python -m lightsout.fetch --list
    python -m lightsout.fetch --tier essentials
    python -m lightsout.fetch --only zimgit-water_en,usda-2015_en --tools
"""
import argparse
import hashlib
import json
import platform
import re
import shutil
import socket
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from . import config

GB = 1e9
BACKOFF = (2, 5, 15)  # seconds to wait before each retry
CHUNK = 1 << 20
SOURCE_NOTE = "Licenses: see docs/licenses.md"


class Refusal(Exception):
    pass


class Bad(Exception):
    pass


def load_manifest(path=None):
    p = Path(path or config.ROOT / "manifest" / "content.json")
    return json.loads(p.read_text(encoding="utf-8"))


def tier_ids(manifest, tier):
    tiers = {t["id"]: t for t in manifest["tiers"]}
    if tier not in tiers:
        raise Refusal("There is no tier called %r. Choose one of: %s." % (tier, ", ".join(tiers)))
    return set(tiers[tier]["includes"]) | {tier}


def tier_items(manifest, tier):
    ids = tier_ids(manifest, tier)
    return [i for i in manifest["items"] if i["tier"] in ids]


def gb(n):
    return "%.1f" % (n / GB)


def print_list(manifest):
    print("%-11s %5s %8s %11s  %s" % ("Tier", "Items", "Size GB", "Total GB", "What it is for"))
    for t in manifest["tiers"]:
        own = [i for i in manifest["items"] if i["tier"] == t["id"]]
        total = sum(i["bytes"] for i in tier_items(manifest, t["id"]))
        print("%-11s %5d %8s %11s  %s" % (t["name"], len(own), gb(sum(i["bytes"] for i in own)), gb(total), t["for"]))
    print("\nTiers add up: each one includes the ones above it. Use --tier NAME (for example --tier pocket).")
    extras = [i for i in manifest["items"] if i["tier"] == "extra"]
    if extras:
        print("\nExtras (only downloaded if you ask for them with --only ID):")
        for i in extras:
            print("  %-42s %6s GB  %s" % (i["id"], gb(i["bytes"]), i["title"]))


def platform_key():
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "macos"}.get(platform.system())
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "x64": "x86_64", "arm64": "arm64", "aarch64": "aarch64"}.get(machine)
    if system == "macos" and arch == "aarch64":
        arch = "arm64"
    if system == "linux" and arch == "arm64":
        arch = "aarch64"
    return "%s-%s" % (system, arch)


class Net:
    """Small wrapper so tests can hand in their own opener and skip the waiting."""

    def __init__(self, opener=None, out=print):
        self.opener = opener or urllib.request.build_opener()
        self.out = out

    def open(self, url, headers=None, method="GET", timeout=60):
        req = urllib.request.Request(url, headers=dict(headers or {}), method=method)
        req.add_header("User-Agent", "lights-out-library/0.1")
        return self.opener.open(req, timeout=timeout)

    def retry(self, fn, what):
        for attempt in range(len(BACKOFF) + 1):
            try:
                return fn()
            except urllib.error.HTTPError as e:
                if e.code < 500 and e.code != 429:
                    raise
                err = e
            except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, OSError) as e:
                err = e
            if attempt == len(BACKOFF):
                raise err
            self.out("  Network hiccup while %s (%s). Trying again in %d seconds ..." % (what, err, BACKOFF[attempt]))
            time.sleep(BACKOFF[attempt])

    def text(self, url):
        def go():
            with self.open(url) as r:
                return r.read().decode("utf-8", "replace")
        return self.retry(go, "reading " + url.rsplit("/", 1)[-1])

    def size(self, url):
        def go():
            with self.open(url, method="HEAD") as r:
                return int(r.headers.get("Content-Length") or -1)
        return self.retry(go, "checking size")


def parse_sha(text, name):
    for line in text.splitlines():
        parts = line.split()
        if parts and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            return parts[0].lower()
    raise Bad("the checksum file for %s is not in the expected format" % name)


def newest_in_index(net, dir_url, item_id):
    """Kiwix replaces files with newer dated ones, so look for <id>_YYYY-MM[a-z].zim in the folder listing."""
    html = net.text(dir_url)
    pat = re.compile(r"^%s_(\d{4}-\d{2}[a-z]?)\.zim$" % re.escape(item_id))
    names = {m for m in re.findall(r'href="([^"?/]+\.zim)"', html) if pat.match(m)}
    return max(names, key=lambda n: pat.match(n).group(1)) if names else None


def resolve(net, base, item, out=print):
    """Returns (file name, url, sha256) for the pinned file, or the newest one if the pinned file is gone."""
    dir_url = base + item["dir"] + "/"
    name = item["file"]
    try:
        return name, dir_url + name, parse_sha(net.text(dir_url + name + ".sha256"), name)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    newer = newest_in_index(net, dir_url, item["id"])
    if not newer:
        raise Bad("%s is no longer on the server and no newer copy was found" % name)
    out("  Kiwix no longer has %s. Using the newer %s instead." % (name, newer))
    return newer, dir_url + newer, parse_sha(net.text(dir_url + newer + ".sha256"), newer)


def file_hash(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


class Progress:
    def __init__(self, total, start, out):
        self.total, self.start, self.t0, self.last, self.out = total, start, time.time(), 0, out
        self.tty = sys.stdout.isatty()

    def update(self, done, final=False):
        now = time.time()
        if not final and now - self.last < (0.5 if self.tty else 10):
            return
        self.last = now
        rate = (done - self.start) / max(now - self.t0, 1e-6) / 1e6
        pct = 100.0 * done / self.total if self.total > 0 else 0.0
        line = "  %5.1f%%  %6.2f GB of %.2f GB  %5.1f MB/s" % (pct, done / GB, max(self.total, 0) / GB, rate)
        if self.tty:
            sys.stdout.write("\r" + line + ("\n" if final else ""))
            sys.stdout.flush()
        else:
            self.out(line)


def download(net, url, final, out=print):
    """Download url into <final>.part (resuming if it exists). Returns the .part path."""
    part = final.with_name(final.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)

    def go():
        have = part.stat().st_size if part.exists() else 0
        headers = {"Range": "bytes=%d-" % have} if have else {}
        try:
            r = net.open(url, headers, timeout=60)
        except urllib.error.HTTPError as e:
            if e.code == 416 and have:
                if (e.headers.get("Content-Range") or "").endswith("/%d" % have):
                    return  # the part file already holds the whole file
                part.write_bytes(b"")  # stale part file: start over
                return go()
            raise
        with r:
            if have and r.status == 206:
                mode, total = "ab", have + int(r.headers.get("Content-Length") or 0)
            else:  # server ignored Range, or nothing to resume
                mode, have = "wb", 0
                total = int(r.headers.get("Content-Length") or 0)
            prog = Progress(total, have, out)
            done = have
            with open(part, mode) as f:
                while True:
                    block = r.read(CHUNK)
                    if not block:
                        break
                    f.write(block)
                    done += len(block)
                    prog.update(done)
            prog.update(done, final=True)
            if total and done < total:
                raise ConnectionError("the connection dropped at %d of %d bytes" % (done, total))

    net.retry(go, "downloading " + final.name)
    return part


def dest_zim_bytes(dest):
    return sum(p.stat().st_size for p in config.find_zims(dest))


def free_space(path):
    p = Path(path).resolve()
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(p).free


def safe_extract(archive, target):
    target = Path(target).resolve()
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not (target / name).resolve().is_relative_to(target):
                    raise Bad("the download contains an unsafe path (%s)" % name)
            z.extractall(target)
    else:
        with tarfile.open(archive) as t:
            for m in t.getmembers():
                if not (target / m.name).resolve().is_relative_to(target):
                    raise Bad("the download contains an unsafe path (%s)" % m.name)
            if hasattr(tarfile, "data_filter"):
                t.extractall(target, filter="data")
            else:
                t.extractall(target)


def fetch_tools(net, manifest, tools_dir, base=None, out=print):
    info = manifest["tools"]["kiwix-tools"]
    key = platform_key()
    plat = info["platforms"].get(key)
    if not plat:
        raise Refusal("There is no ready-made Kiwix tool for this computer (%s). "
                      "See https://www.kiwix.org/en/applications/ to install kiwix-serve yourself." % key)
    tools_dir = Path(tools_dir)
    if any(p.is_file() and p.name in ("kiwix-serve", "kiwix-serve.exe") for p in tools_dir.rglob("kiwix-serve*")):
        out("Book server (kiwix-serve) is already installed.")
        return
    url = (base or info["base"]) + plat["file"]
    archive = tools_dir / plat["file"]
    out("Downloading the book server (kiwix-tools %s, %.0f MB, %s) ..." % (info["version"], plat["bytes"] / 1e6, info["license"]))
    part = download(net, url, archive, out)
    # Kiwix publishes only an MD5 for the tools (no SHA-256), so MD5 is the strongest check available here.
    if file_hash(part, "md5") != plat["md5"]:
        part.replace(archive.with_name(archive.name + ".bad"))
        raise Bad("the book server download did not match its published checksum; kept as %s.bad" % archive.name)
    part.replace(archive)
    safe_extract(archive, tools_dir)
    for p in tools_dir.rglob("kiwix-serve*"):
        if p.is_file():
            p.chmod(p.stat().st_mode | 0o755)
    out("Book server installed in %s" % tools_dir)


def select_items(manifest, args):
    chosen = []
    if args.tier:
        chosen += tier_items(manifest, args.tier)
    if args.only:
        by_id = {i["id"]: i for i in manifest["items"]}
        for item_id in [s.strip() for s in args.only.split(",") if s.strip()]:
            if item_id not in by_id:
                raise Refusal("Unknown book id %r. Run with --list to see tiers, or check docs for the ids." % item_id)
            chosen.append(by_id[item_id])
    seen, out = set(), []
    for i in chosen:
        if i["id"] not in seen:
            seen.add(i["id"])
            out.append(i)
    return out


def verify_files(net, manifest, dest, base, items=None, out=print):
    items = items or manifest["items"]
    bad = checked = 0
    for item in items:
        for p in config.find_zims(dest):
            if not p.name.startswith(item["id"] + "_"):
                continue
            checked += 1
            try:
                want = parse_sha(net.text("%s%s/%s.sha256" % (base, item["dir"], p.name)), p.name)
            except (urllib.error.URLError, Bad) as e:
                out("?? %s: could not get the published checksum (%s)" % (p.name, e))
                bad += 1
                continue
            if file_hash(p, "sha256") == want:
                out("OK  %s" % p.name)
            else:
                out("BAD %s: does not match the published checksum. Download it again." % p.name)
                bad += 1
    out("\nChecked %d file%s, %d problem%s." % (checked, "" if checked == 1 else "s", bad, "" if bad == 1 else "s"))
    return 1 if bad else 0


def main(argv=None, *, opener=None, source_base=None, tools_base=None, tools_dir=None, out=print):
    ap = argparse.ArgumentParser(prog="fetch", description="Download books for the Lights Out Library.")
    ap.add_argument("--list", action="store_true", help="show the tiers and what they cost")
    ap.add_argument("--tier", help="download a tier (includes the smaller tiers)")
    ap.add_argument("--only", help="comma-separated book ids (any, including extras)")
    ap.add_argument("--tools", action="store_true", help="download the Kiwix book server for this computer")
    ap.add_argument("--no-tools", action="store_true", help="with --tier: do not also download the book server")
    ap.add_argument("--dest", help="folder for the books (default: content_dir from config)")
    ap.add_argument("--dry-run", action="store_true", help="show what would be downloaded; change nothing")
    ap.add_argument("--verify", action="store_true", help="re-check downloaded books against their published SHA-256")
    ap.add_argument("--yes", action="store_true", help="do not ask before starting")
    ap.add_argument("--mirror", metavar="URL", help="download the big files from a Kiwix mirror's zim folder, e.g. "
                    "https://mirrors.dotsrc.org/kiwix/zim/ (checksums still come from Kiwix itself)")
    ap.add_argument("--manifest", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        cfg = config.load_config()
        return _run(args, manifest, cfg, Net(opener, out), source_base, tools_base, tools_dir, out)
    except (Refusal, config.ConfigError) as e:
        out("\n%s" % e)
        return 2
    except KeyboardInterrupt:
        out("\nStopped. Run the same command again to carry on where it left off.")
        return 130


def _run(args, manifest, cfg, net, source_base, tools_base, tools_dir, out):
    if args.list:
        print_list(manifest)
        return 0
    base = source_base or manifest["source"]["base"]
    dest = Path(args.dest).resolve() if args.dest else cfg["content_dir"]
    tools_dir = Path(tools_dir or cfg["root"] / "tools" / "kiwix")
    if args.verify:
        return verify_files(net, manifest, dest, base, select_items(manifest, args) or None, out)
    items = select_items(manifest, args)
    want_tools = args.tools or (bool(args.tier) and not args.no_tools)
    if not items and not want_tools:
        out("Nothing to do. Try --list to see what is available, then for example --tier pocket.")
        return 2

    todo, have_bytes, resume_bytes = [], 0, 0
    for i in items:
        target = dest / i["file"]
        if target.exists() and target.stat().st_size == i["bytes"]:
            have_bytes += i["bytes"]
        else:
            todo.append(i)
            part = target.with_name(target.name + ".part")
            resume_bytes += part.stat().st_size if part.exists() else 0
    need = sum(i["bytes"] for i in todo) - resume_bytes
    tools_need = 0
    if want_tools:
        plat = manifest["tools"]["kiwix-tools"]["platforms"].get(platform_key())
        tools_need = plat["bytes"] * 2 if plat else 0  # the archive plus its unpacked copy
    ask_bytes = manifest["ask"]["allowance_bytes"] if cfg["ask"]["enabled"] else 0
    limit = manifest.get("limit_gb", 500) * GB

    out("Books to download: %d (%s GB). Already have: %d (%s GB)." % (len(todo), gb(sum(i["bytes"] for i in todo)), len(items) - len(todo), gb(have_bytes)))
    if want_tools:
        out("Book server (Kiwix) will be downloaded for this computer.")
    for i in todo:
        out("  %6s GB  %s" % (gb(i["bytes"]), i["title"]))
    if args.dry_run:
        out("\nDry run: nothing downloaded. Total to download: %s GB." % gb(need + tools_need // 2))
        return 0

    existing = dest_zim_bytes(dest)
    if existing + need + ask_bytes > limit:
        raise Refusal("That would use %s GB, over the %s GB limit (%s GB of books already here%s). "
                      "Pick a smaller tier or fewer books." % (
                          gb(existing + need + ask_bytes), "%g" % manifest.get("limit_gb", 500), gb(existing),
                          ", plus %s GB kept for the AI model" % gb(ask_bytes) if ask_bytes else ""))
    free = free_space(dest)
    if free < need + tools_need:
        raise Refusal("Not enough free disk space: need %s GB, only %s GB free on that drive. "
                      "Free some space or use --dest to pick another drive." % (gb(need + tools_need), gb(free)))
    if not args.yes:
        if not sys.stdin or not sys.stdin.isatty():
            raise Refusal("Add --yes to start the download.")
        if input("\nStart downloading %s GB? [y/N] " % gb(need + tools_need // 2)).strip().lower() not in ("y", "yes"):
            out("Cancelled. Nothing was downloaded.")
            return 0

    failures = []
    if want_tools:
        try:
            fetch_tools(net, manifest, tools_dir, tools_base, out)
        except (Bad, urllib.error.URLError, OSError, zipfile.BadZipFile, tarfile.TarError) as e:
            out("PROBLEM with the book server download: %s" % e)
            failures.append("kiwix-tools")
    done = 0
    for n, item in enumerate(todo, 1):
        out("\n[%d/%d] %s" % (n, len(todo), item["title"]))
        out("  License: %s (%s)" % (item["license"], item["redistribution"]))
        try:
            name, url, want = resolve(net, base, item, out)
            if args.mirror:
                # Kiwix's own server can be slow. A mirror serves the same file; the SHA-256 above
                # came from Kiwix, so a wrong or tampered mirror copy is still caught.
                url = "%s/%s/%s" % (args.mirror.rstrip("/"), item["dir"], name)
            final = dest / name
            if final.exists() and final.stat().st_size == net.size(url):
                out("  Already have %s." % name)
                continue
            part = download(net, url, final, out)
            if file_hash(part, "sha256") != want:
                bad = final.with_name(final.name + ".bad")
                part.replace(bad)
                out("  PROBLEM: the file does not match its published SHA-256. Kept as %s for inspection; "
                    "run again to download a fresh copy." % bad.name)
                failures.append(item["id"])
                continue
            part.replace(final)
            out("  Done. SHA-256 verified.")
            done += 1
        except (Bad, urllib.error.URLError, OSError) as e:
            out("  PROBLEM: %s" % e)
            failures.append(item["id"])

    out("\nSummary: %d downloaded, %d already present, %d failed." % (done, len(items) - len(todo), len(failures)))
    if failures:
        out("Failed: %s. Run the same command again to retry." % ", ".join(failures))
    out(SOURCE_NOTE)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
