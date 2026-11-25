"""Copy the shared JPS design tokens into site/css/tokens.css.

The tokens are owned by the JPS Console (src/jps_console/static/tokens.css in the jps-console repo).
Lights Out uses them as they are and never edits its copy. To pick up a change there:

    python scripts/sync_tokens.py PATH/TO/jps-console

That writes site/css/tokens.css with a header naming the source commit and the file's SHA-256.
Exactly one thing is changed on the way: the font paths, because the fonts sit one folder up
here (site/fonts/) instead of beside the file. tests/test_tokens.py checks that the copy still
matches the recorded hash, so a hand edit fails CI.

Anything Lights Out needs that the shared set lacks goes in site/css/lightsout-tokens.css,
listed there as a gap to raise with the Console, not here.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "site" / "css" / "tokens.css"
SOURCE = Path("src") / "jps_console" / "static" / "tokens.css"
FONT_FROM, FONT_TO = 'url("fonts/', 'url("../fonts/'
MARK = "/* --- copied from jps-console below this line; do not edit --- */\n"


def header(commit, digest):
    return (
        "/* Shared JPS design tokens, vendored from the JPS Console.\n"
        "   Source: JaxsonPierceSolutions/jps-console, src/jps_console/static/tokens.css\n"
        "   Commit: %s\n"
        "   SHA-256 of the source file: %s\n"
        "   Changed on copy: the two font paths only (fonts/ becomes ../fonts/).\n"
        "   Update with scripts/sync_tokens.py; never edit by hand. Lights Out additions are in\n"
        "   lightsout-tokens.css. Values from IBM Carbon are used under Apache-2.0 (see NOTICE). */\n"
        % (commit, digest)
    )


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    console = Path(argv[1]).resolve()
    src = (console / SOURCE).read_bytes()
    commit = subprocess.run(["git", "-C", str(console), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    text = src.decode("utf-8").replace("\r\n", "\n")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    DEST.write_text(header(commit, digest) + MARK + text.replace(FONT_FROM, FONT_TO),
                    encoding="utf-8", newline="\n")
    print("wrote %s from %s (%s)" % (DEST.relative_to(ROOT), commit[:7], digest[:12]))


if __name__ == "__main__":
    main(sys.argv)
