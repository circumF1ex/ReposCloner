"""Tests for reposcloner.config — defaults, debug switch, save/load."""

import json

from reposcloner.config import DEFAULT_CONFIG, is_debug_enabled, load_config, save_config


def test_defaults_ru_and_no_debug():
    assert DEFAULT_CONFIG['language'] == 'ru'
    assert DEFAULT_CONFIG['debug'] is False


def test_debug_off_by_default():
    assert is_debug_enabled({}) is False
    assert is_debug_enabled(None) is False
    assert is_debug_enabled({'debug': False}) is False


def test_debug_via_config():
    assert is_debug_enabled({'debug': True}) is True


def test_debug_via_env(monkeypatch):
    monkeypatch.setenv('REPOSCLONER_DEBUG', '1')
    assert is_debug_enabled({}) is True
    monkeypatch.setenv('REPOSCLONER_DEBUG', 'off')
    assert is_debug_enabled({}) is False


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    path = str(tmp_path / 'config.json')
    monkeypatch.setattr('reposcloner.config.CONFIG_FILE', path)
    save_config({**DEFAULT_CONFIG, 'language': 'en', 'debug': True}, path)
    loaded = load_config()
    assert loaded['language'] == 'en'
    assert loaded['debug'] is True
    # File content is human-readable JSON.
    raw = json.loads(open(path, encoding='utf-8').read())
    assert raw['language'] == 'en'
