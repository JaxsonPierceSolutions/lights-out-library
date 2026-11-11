import hashlib
import io
import json
import tarfile
import zipfile

import pytest

from helpers import FileServer
from lightsout import fetch


def sha(b):
    return hashlib.sha256(b).hexdigest()


def item(i, tier, name, data, dir="other"):
    return {"id": i, "title": "Book " + i, "tier": tier, "shelf": "s", "dir": dir, "file": name,
            "bytes": len(data), "license": "CC TEST", "redistribution": "open", "note": ""}


A = b"alpha-book-data" * 400
B = b"bravo-book-data" * 300
C = b"charlie-extra!!" * 200


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(fetch, "BACKOFF", (0, 0))


class World:
    pass


@pytest.fixture
def world(tmp_path):
    items = [item("alpha_en", "pocket", "alpha_en_2024-01.zim", A),
             item("bravo_en", "essentials", "bravo_en_2024-02.zim", B, "wikipedia"),
             item("charlie_en", "extra", "charlie_en_2024-03.zim", C)]
    manifest = {"schema": 1, "limit_gb": 500, "source": {"base": "https://download.kiwix.org/zim/"},
                "tiers": [{"id": "pocket", "name": "Pocket", "includes": [], "for": "x"},
                          {"id": "essentials", "name": "Essentials", "includes": ["pocket"], "for": "y"}],
                "items": items, "ask": {"allowance_bytes": 6000000000},
                "tools": {"kiwix-tools": {"version": "9", "license": "GPL", "base": "https://example.invalid/", "platforms": {}}}}
    files = {"/zim/other/alpha_en_2024-01.zim": A, "/zim/other/alpha_en_2024-01.zim.sha256": "%s  alpha_en_2024-01.zim\n" % sha(A),
             "/zim/wikipedia/bravo_en_2024-02.zim": B, "/zim/wikipedia/bravo_en_2024-02.zim.sha256": "%s  bravo_en_2024-02.zim\n" % sha(B),
             "/zim/other/charlie_en_2024-03.zim": C, "/zim/other/charlie_en_2024-03.zim.sha256": "%s  charlie_en_2024-03.zim\n" % sha(C)}
    fs = FileServer(files)
    w = World()
    w.manifest, w.files, w.fs, w.dest, w.tmp, w.out = manifest, files, fs, tmp_path / "dest", tmp_path, []

    def run(*args, **kw):
        w.out.clear()
        mpath = tmp_path / "m.json"
        mpath.write_text(json.dumps(manifest))
        return fetch.main(["--manifest", str(mpath), "--dest", str(w.dest), *args],
                          source_base=fs.base + "zim/", out=w.out.append, **kw)
    w.run = run
    w.text = lambda: "\n".join(w.out)
    yield w
    fs.close()


def test_list_matches_manifest(capsys):
    assert fetch.main(["--list"]) == 0
    shown = capsys.readouterr().out
    m = fetch.load_manifest()
    for t in m["tiers"]:
        total = sum(i["bytes"] for i in fetch.tier_items(m, t["id"]))
        assert ("%.1f" % (total / 1e9)) in shown and t["name"] in shown
    for extra in (i for i in m["items"] if i["tier"] == "extra"):
        assert extra["id"] in shown


def test_download_and_verify(world):
    assert world.run("--tier", "essentials", "--no-tools", "--yes") == 0
    assert (world.dest / "alpha_en_2024-01.zim").read_bytes() == A
    assert (world.dest / "bravo_en_2024-02.zim").read_bytes() == B
    assert not list(world.dest.glob("*.part")) and not (world.dest / "charlie_en_2024-03.zim").exists()
    text = world.text()
    assert "SHA-256 verified" in text and "License: CC TEST" in text and "Licenses: see docs/licenses.md" in text
    hits_before = len(world.fs.hits)
    assert world.run("--tier", "essentials", "--no-tools", "--yes") == 0  # second run: nothing to do
    assert len(world.fs.hits) == hits_before
    assert world.run("--verify") == 0 and "OK  alpha_en_2024-01.zim" in world.text()


def test_extras_by_id(world):
    assert world.run("--only", "charlie_en", "--yes") == 0
    assert (world.dest / "charlie_en_2024-03.zim").read_bytes() == C
    assert world.run("--only", "nonesuch", "--yes") == 2


def test_resume_from_part(world):
    world.dest.mkdir()
    (world.dest / "alpha_en_2024-01.zim.part").write_bytes(A[:1000])
    assert world.run("--only", "alpha_en", "--yes") == 0
    assert (world.dest / "alpha_en_2024-01.zim").read_bytes() == A
    assert ("GET", "/zim/other/alpha_en_2024-01.zim", "bytes=1000-") in world.fs.hits


def test_bad_checksum_kept_as_bad(world):
    world.files["/zim/other/alpha_en_2024-01.zim.sha256"] = "%s  alpha_en_2024-01.zim\n" % ("0" * 64)
    assert world.run("--only", "alpha_en", "--yes") == 1
    assert not (world.dest / "alpha_en_2024-01.zim").exists()
    assert (world.dest / "alpha_en_2024-01.zim.bad").read_bytes() == A
    assert "does not match" in world.text()


def test_verify_flags_corrupt_file(world):
    world.dest.mkdir()
    (world.dest / "alpha_en_2024-01.zim").write_bytes(A[:-1] + b"X")
    assert world.run("--verify") == 1 and "BAD alpha_en_2024-01.zim" in world.text()


def test_pinned_404_uses_newest_dated_file(world):
    new = b"newer alpha" * 50
    for k in ("/zim/other/alpha_en_2024-01.zim", "/zim/other/alpha_en_2024-01.zim.sha256"):
        del world.files[k]
    world.files["/zim/other/alpha_en_2025-02.zim"] = new
    world.files["/zim/other/alpha_en_2025-02.zim.sha256"] = "%s  alpha_en_2025-02.zim" % sha(new)
    world.files["/zim/other/alpha_en_2024-12.zim"] = b"old"
    world.files["/zim/other/"] = ('<a href="alpha_en_2024-12.zim">x</a> <a href="alpha_en_2025-02.zim">x</a> '
                                  '<a href="alpha_en_nopic_2026-01.zim">other book</a> <a href="alpha_en_2025-01.zim.sha256">s</a>')
    assert world.run("--only", "alpha_en", "--yes") == 0
    assert (world.dest / "alpha_en_2025-02.zim").read_bytes() == new
    assert "newer alpha_en_2025-02.zim" in world.text()


def test_dry_run_touches_nothing(world):
    assert world.run("--tier", "essentials", "--dry-run") == 0
    assert not world.dest.exists() and world.fs.hits == []
    assert "Dry run" in world.text() and "Book alpha_en" in world.text()


def test_over_limit_refused(world):
    world.manifest["limit_gb"] = 0.00001  # 10 KB, less than the two books together
    assert world.run("--tier", "essentials", "--no-tools", "--yes") == 2
    assert "limit" in world.text() and not world.dest.exists() and world.fs.hits == []


def test_limit_counts_books_already_present(world):
    world.dest.mkdir()
    (world.dest / "zzz_en_2020-01.zim").write_bytes(b"z" * 9000)
    world.manifest["limit_gb"] = 0.000012  # 12 KB: alpha alone (6 KB) would fit only if the 9 KB file were ignored
    assert world.run("--only", "alpha_en", "--yes") == 2


def test_not_enough_disk_space_refused(world, monkeypatch):
    monkeypatch.setattr(fetch, "free_space", lambda p: 10)
    assert world.run("--only", "alpha_en", "--yes") == 2 and "free disk space" in world.text()


def test_no_yes_without_terminal_refused(world):
    assert world.run("--only", "alpha_en") == 2 and not world.dest.exists()


def make_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("kiwix-tools_win-x86_64-9/kiwix-serve.exe", b"MZ fake")
        z.writestr("kiwix-tools_win-x86_64-9/readme.txt", b"hi")
    return buf.getvalue()


def make_tgz():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        data = b"#!/bin/sh\n"
        ti = tarfile.TarInfo("kiwix-serve")
        ti.size = len(data)
        t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


@pytest.mark.parametrize("key,name,maker,exe", [
    ("windows-x86_64", "tools.zip", make_zip, "kiwix-serve.exe"),
    ("linux-x86_64", "tools.tar.gz", make_tgz, "kiwix-serve")])
def test_tools_md5_and_unpack(world, monkeypatch, key, name, maker, exe):
    blob = maker()
    monkeypatch.setattr(fetch, "platform_key", lambda: key)
    world.manifest["tools"]["kiwix-tools"]["platforms"] = {key: {"file": name, "bytes": len(blob), "md5": hashlib.md5(blob).hexdigest()}}
    world.files["/tools/" + name] = blob
    tools = world.tmp / "tools" / "kiwix"
    assert world.run("--tools", "--yes", tools_base=world.fs.base + "tools/", tools_dir=tools) == 0
    assert [p for p in tools.rglob("*") if p.name == exe]
    assert world.run("--tools", "--yes", tools_base=world.fs.base + "tools/", tools_dir=tools) == 0
    assert "already installed" in world.text()


def test_tools_bad_md5_kept_as_bad(world, monkeypatch):
    blob = make_zip()
    monkeypatch.setattr(fetch, "platform_key", lambda: "windows-x86_64")
    world.manifest["tools"]["kiwix-tools"]["platforms"] = {"windows-x86_64": {"file": "t.zip", "bytes": len(blob), "md5": "0" * 32}}
    world.files["/tools/t.zip"] = blob
    tools = world.tmp / "tools" / "kiwix"
    assert world.run("--tools", "--yes", tools_base=world.fs.base + "tools/", tools_dir=tools) == 1
    assert (tools / "t.zip.bad").exists() and not list(tools.rglob("kiwix-serve*"))


def test_unsafe_archive_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../evil.txt", b"x")
    z = tmp_path / "bad.zip"
    z.write_bytes(buf.getvalue())
    with pytest.raises(fetch.Bad):
        fetch.safe_extract(z, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()
