import ast
import sys
import sysconfig
from pathlib import Path

from lightsout import config

ROOT = config.ROOT


def test_key_files_exist():
    assert (ROOT / "manifest" / "content.json").is_file()
    assert (ROOT / "DESIGN.md").is_file()


def is_stdlib(name):
    if hasattr(sys, "stdlib_module_names"):
        return name in sys.stdlib_module_names
    import importlib.util
    spec = importlib.util.find_spec(name)
    return bool(spec) and (spec.origin in ("built-in", "frozen") or Path(spec.origin).is_relative_to(sysconfig.get_paths()["stdlib"])
                           and "site-packages" not in spec.origin)


def test_src_imports_only_standard_library():
    files = list((ROOT / "src").rglob("*.py"))
    assert files
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module]
            else:
                continue
            for n in names:
                top = n.split(".")[0]
                assert top == "lightsout" or is_stdlib(top), "%s imports %s, which is not in the standard library" % (path.name, n)


def test_launchers_have_expected_line_endings():
    for name, crlf in (("start.cmd", True), ("fetch.cmd", True), ("start.sh", False), ("fetch.sh", False)):
        p = ROOT / name
        if p.exists():
            data = p.read_bytes()
            assert (b"\r\n" in data) == crlf, name
