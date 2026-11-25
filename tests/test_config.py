"""lightsout.config: where each setting comes from, and the mistakes it refuses.

Expected values come from outside the code:

- The module's documented order: built-in defaults, then config.json in the project folder,
  then environment variables (each later one wins).
- config.example.json and docs/layers.md ("layers" paths are relative to the project folder;
  LIGHTSOUT_LAYERS is a list like PATH, split on the platform's separator).
- TCP ports are 16-bit numbers; 0 is reserved, so a port to listen on is 1 to 65535 (RFC 6335).
- CLAUDE.md: Ask only talks to an Ollama on this computer, and DeepSeek models are not allowed.
- The JSON spec (RFC 8259): a config file must be a JSON object to hold named settings.
"""
import os
from pathlib import Path

import pytest

from lightsout import config


def write_config(root, text):
    (Path(root) / "config.json").write_text(text, encoding="utf-8")


# ---- defaults, config.json, then the environment -------------------------------------------


def test_with_no_config_file_and_no_environment_the_defaults_apply(tmp_path):
    cfg = config.load_config(root=tmp_path, env={})
    assert cfg["port"] == 8600
    assert cfg["kiwix_port"] == 8601
    assert cfg["content_dir"] == (tmp_path / "content").resolve()
    assert cfg["files_dir"] == (tmp_path / "files").resolve()
    assert cfg["layers"] == []
    assert cfg["open_browser"] is True
    assert cfg["kiwix_url"] is None
    assert cfg["root"] == tmp_path
    assert cfg["ask"]["enabled"] is False
    assert cfg["ask"]["model"] == ""


def test_loading_never_changes_the_built_in_defaults(tmp_path):
    write_config(tmp_path, '{"port": 9000, "ask": {"model": "llama3.1:8b"}}')
    config.load_config(root=tmp_path, env={})
    assert config.DEFAULTS["port"] == 8600
    assert config.DEFAULTS["ask"]["model"] == ""


def test_config_json_overrides_a_default_and_keeps_the_others(tmp_path):
    write_config(tmp_path, '{"port": 9000, "open_browser": false}')
    cfg = config.load_config(root=tmp_path, env={})
    assert cfg["port"] == 9000
    assert cfg["open_browser"] is False
    assert cfg["kiwix_port"] == 8601


def test_an_ask_block_merges_into_the_ask_defaults_instead_of_replacing_them(tmp_path):
    write_config(tmp_path, '{"ask": {"enabled": true, "model": "llama3.1:8b"}}')
    ask = config.load_config(root=tmp_path, env={})["ask"]
    assert ask["enabled"] is True
    assert ask["model"] == "llama3.1:8b"
    assert ask["embed_model"] == "nomic-embed-text"
    assert ask["ollama_url"] == "http://127.0.0.1:11434"


def test_a_config_file_saved_with_a_byte_order_mark_is_read(tmp_path):
    # Windows Notepad's "UTF-8 with BOM" puts EF BB BF first; RFC 8259 lets a parser ignore it.
    (tmp_path / "config.json").write_bytes(b'\xef\xbb\xbf{"port": 9100}')
    assert config.load_config(root=tmp_path, env={})["port"] == 9100


def test_the_example_config_loads_as_is(tmp_path):
    example = (config.ROOT / "config.example.json").read_text(encoding="utf-8")
    write_config(tmp_path, example)
    cfg = config.load_config(root=tmp_path, env={})
    assert cfg["port"] == 8600
    assert cfg["ask"]["enabled"] is False


def test_the_environment_wins_over_config_json(tmp_path):
    write_config(tmp_path, '{"port": 9000, "kiwix_port": 9001, "content_dir": "from-file"}')
    env = {"LIGHTSOUT_PORT": "9200", "LIGHTSOUT_KIWIX_PORT": "9201", "LIGHTSOUT_CONTENT_DIR": "from-env"}
    cfg = config.load_config(root=tmp_path, env=env)
    assert cfg["port"] == 9200
    assert cfg["kiwix_port"] == 9201
    assert cfg["content_dir"] == (tmp_path / "from-env").resolve()


def test_an_empty_environment_variable_is_ignored(tmp_path):
    write_config(tmp_path, '{"port": 9000}')
    assert config.load_config(root=tmp_path, env={"LIGHTSOUT_PORT": ""})["port"] == 9000


@pytest.mark.parametrize("value, expected", [("1", False), ("0", True), ("yes", True)])
def test_LIGHTSOUT_NO_BROWSER_turns_the_browser_off_only_when_it_is_1(tmp_path, value, expected):
    assert config.load_config(root=tmp_path, env={"LIGHTSOUT_NO_BROWSER": value})["open_browser"] is expected


def test_an_absolute_content_dir_is_kept_as_given(tmp_path):
    elsewhere = (tmp_path / "usb" / "books").resolve()
    cfg = config.load_config(root=tmp_path / "project", env={"LIGHTSOUT_CONTENT_DIR": str(elsewhere)})
    assert cfg["content_dir"] == elsewhere


# ---- layers --------------------------------------------------------------------------------


def test_config_json_layers_are_relative_to_the_project_folder(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    write_config(root, '{"layers": ["../our-house", "extra"]}')
    cfg = config.load_config(root=root, env={})
    assert cfg["layers"] == [(tmp_path / "our-house").resolve(), (root / "extra").resolve()]


def test_LIGHTSOUT_LAYERS_is_split_like_PATH_and_replaces_the_files_list(tmp_path):
    write_config(tmp_path, '{"layers": ["from-file"]}')
    env = {"LIGHTSOUT_LAYERS": os.pathsep.join(["one", "", "two"])}
    cfg = config.load_config(root=tmp_path, env=env)
    assert cfg["layers"] == [(tmp_path / "one").resolve(), (tmp_path / "two").resolve()]


def test_layers_that_are_not_a_list_are_refused(tmp_path):
    write_config(tmp_path, '{"layers": "our-house"}')
    with pytest.raises(config.ConfigError, match="list of folders"):
        config.load_config(root=tmp_path, env={})


# ---- the book server's address -------------------------------------------------------------


def test_LIGHTSOUT_KIWIX_URL_is_used_without_its_trailing_slash(tmp_path):
    cfg = config.load_config(root=tmp_path, env={"LIGHTSOUT_KIWIX_URL": "http://127.0.0.1:9999/kiwix/"})
    assert cfg["kiwix_url"] == "http://127.0.0.1:9999/kiwix"
    assert config.kiwix_base(cfg) == "http://127.0.0.1:9999/kiwix"


def test_without_a_kiwix_url_the_book_server_is_on_this_computer_at_kiwix_port(tmp_path):
    cfg = config.load_config(root=tmp_path, env={"LIGHTSOUT_KIWIX_PORT": "8701"})
    assert config.kiwix_base(cfg) == "http://127.0.0.1:8701"


# ---- mistakes it refuses, with a message for the person running it -------------------------


def test_a_config_file_that_is_not_json_is_refused_with_how_to_fix_it(tmp_path):
    write_config(tmp_path, '{"port": 9000,}')
    with pytest.raises(config.ConfigError, match="not valid JSON.*delete it to use the defaults"):
        config.load_config(root=tmp_path, env={})


@pytest.mark.parametrize("text", ["[8600]", '"port"', "8600", "null"])
def test_a_config_file_that_is_not_a_json_object_is_refused(tmp_path, text):
    write_config(tmp_path, text)
    with pytest.raises(config.ConfigError, match="must contain a JSON object"):
        config.load_config(root=tmp_path, env={})


@pytest.mark.parametrize("ask", ['"on"', "true", "[]"])
def test_an_ask_setting_that_is_not_an_object_is_refused(tmp_path, ask):
    write_config(tmp_path, '{"ask": %s}' % ask)
    with pytest.raises(config.ConfigError, match='"ask" must be an object'):
        config.load_config(root=tmp_path, env={})


@pytest.mark.parametrize("name, env", [("port", "LIGHTSOUT_PORT"), ("kiwix_port", "LIGHTSOUT_KIWIX_PORT")])
@pytest.mark.parametrize("value", ["eighty", "86.5", "0x2198"])
def test_a_port_that_is_not_a_whole_number_is_refused_naming_the_setting(tmp_path, name, env, value):
    with pytest.raises(config.ConfigError, match="^%s must be a whole number, not '%s'" % (name, value)):
        config.load_config(root=tmp_path, env={env: value})


def test_a_port_of_null_in_config_json_is_refused(tmp_path):
    write_config(tmp_path, '{"port": null}')
    with pytest.raises(config.ConfigError, match="port must be a whole number, not None"):
        config.load_config(root=tmp_path, env={})


@pytest.mark.parametrize("value", ["0", "65536", "-1", "70000"])
def test_a_port_outside_1_to_65535_is_refused(tmp_path, value):
    with pytest.raises(config.ConfigError, match="port must be between 1 and 65535"):
        config.load_config(root=tmp_path, env={"LIGHTSOUT_PORT": value})


@pytest.mark.parametrize("value", ["1", "65535"])
def test_the_lowest_and_highest_ports_are_allowed(tmp_path, value):
    assert config.load_config(root=tmp_path, env={"LIGHTSOUT_PORT": value})["port"] == int(value)


def test_a_deepseek_embedding_model_is_refused_too(tmp_path):
    write_config(tmp_path, '{"ask": {"embed_model": "DeepSeek-embed"}}')
    with pytest.raises(config.ConfigError, match="ask.embed_model .*DeepSeek models are not allowed"):
        config.load_config(root=tmp_path, env={})


def test_an_ollama_url_with_no_host_is_refused_and_the_message_shows_what_was_given(tmp_path):
    write_config(tmp_path, '{"ask": {"ollama_url": "not a url"}}')
    with pytest.raises(config.ConfigError, match="not 'not a url'"):
        config.load_config(root=tmp_path, env={})


# ---- finding the books ---------------------------------------------------------------------


def test_find_zims_looks_one_folder_deep_and_sorts_by_file_name(tmp_path):
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "deep").mkdir()
    for p in ["zeta.zim", "b/alpha.zim", "b/deep/too-deep.zim", "notes.txt"]:
        (tmp_path / p).write_bytes(b"")
    (tmp_path / "folder.zim").mkdir()  # a folder named .zim is not a book
    assert [p.name for p in config.find_zims(tmp_path)] == ["alpha.zim", "zeta.zim"]


def test_find_zims_on_a_missing_folder_finds_nothing(tmp_path):
    assert config.find_zims(tmp_path / "no-such-folder") == []
