import json
import urllib.parse

import pytest

from lightsout import config

M = json.load(open(config.ROOT / "manifest" / "content.json", encoding="utf-8"))
ITEM_KEYS = {"id", "title", "tier", "shelf", "dir", "file", "bytes", "license"}


def cumulative(tier_id):
    tiers = {t["id"]: t for t in M["tiers"]}
    ids = set(tiers[tier_id]["includes"]) | {tier_id}
    return sum(i["bytes"] for i in M["items"] if i["tier"] in ids)


def test_top_level_keys():
    assert {"schema", "limit_gb", "source", "tiers", "shelves", "items", "tools", "ask"} <= set(M)
    assert M["limit_gb"] == 500


def test_items_schema():
    ids = [i["id"] for i in M["items"]]
    assert len(ids) == len(set(ids))
    tiers = {t["id"] for t in M["tiers"]} | {"extra"}
    shelves = {s["id"] for s in M["shelves"]}
    for i in M["items"]:
        assert ITEM_KEYS <= set(i), i["id"]
        assert i["tier"] in tiers and i["shelf"] in shelves, i["id"]
        assert i["file"].startswith(i["id"] + "_") and i["file"].endswith(".zim"), i["id"]
        assert isinstance(i["bytes"], int) and i["bytes"] > 0, i["id"]
        assert i["license"].strip(), i["id"]


def test_tier_includes_exist():
    known = {t["id"] for t in M["tiers"]}
    for t in M["tiers"]:
        assert set(t["includes"]) <= known and t["id"] not in t["includes"]


def test_urls_are_https_kiwix_only():
    urls = [M["source"]["base"], M["tools"]["kiwix-tools"]["base"]]
    urls += [M["source"]["base"] + i["dir"] + "/" + i["file"] for i in M["items"]]
    urls += [M["tools"]["kiwix-tools"]["base"] + p["file"] for p in M["tools"]["kiwix-tools"]["platforms"].values()]
    for u in urls:
        parts = urllib.parse.urlsplit(u)
        assert parts.scheme == "https" and parts.hostname == "download.kiwix.org", u


def test_tools_have_md5():
    for key, p in M["tools"]["kiwix-tools"]["platforms"].items():
        assert len(p["md5"]) == 32 and p["bytes"] > 0 and p["file"], key


@pytest.mark.parametrize("tier", [t["id"] for t in M["tiers"]])
def test_every_tier_fits_under_limit(tier):
    tools = max(p["bytes"] for p in M["tools"]["kiwix-tools"]["platforms"].values())
    total = cumulative(tier) + tools + M["ask"]["allowance_bytes"]
    assert total < M["limit_gb"] * 1e9, "%s needs %.1f GB" % (tier, total / 1e9)


def test_no_banned_model_names():
    text = json.dumps([M["items"], M["ask"]]).lower()
    assert "deepseek" not in text and "qwen" not in text
    for m in M["ask"]["suggested_models"] + [M["ask"]["embedding_model"]]:
        assert not {"deepseek", "qwen"} & set(m["name"].lower().replace(":", " ").replace("-", " ").split())


def test_ask_off_by_default():
    assert M["ask"]["default_enabled"] is False
