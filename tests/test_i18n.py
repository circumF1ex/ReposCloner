"""Tests for reposcloner.i18n — no git, no network."""

from reposcloner.i18n import AVAILABLE_LANGUAGES, DEFAULT_LANGUAGE, STRINGS, get_lang, t


def test_russian_is_primary_default():
    assert DEFAULT_LANGUAGE == 'ru'
    assert get_lang({}) == 'ru'
    assert get_lang(None) == 'ru'
    assert get_lang({'language': 'xx'}) == 'ru'


def test_english_selected():
    assert get_lang({'language': 'en'}) == 'en'


def test_key_parity_between_languages():
    ru_keys = set(STRINGS['ru'])
    en_keys = set(STRINGS['en'])
    assert ru_keys == en_keys, (
        f"RU-only: {sorted(ru_keys - en_keys)}; EN-only: {sorted(en_keys - ru_keys)}")


def test_no_empty_strings():
    for lang, table in STRINGS.items():
        for key, value in table.items():
            assert value.strip(), f"{lang}.{key} is empty"


def test_format_placeholders():
    assert '5' in t('clone_btn', 'ru', n=5)
    assert '5' in t('clone_btn', 'en', n=5)
    assert t('goodbye', 'ru') == 'До свидания!'
    assert t('goodbye', 'en') == 'Goodbye!'


def test_missing_key_returns_key():
    assert t('no_such_key', 'ru') == 'no_such_key'


def test_available_languages_matches_strings():
    assert set(AVAILABLE_LANGUAGES) == set(STRINGS)
