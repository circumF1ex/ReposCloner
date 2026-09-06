"""Tests for reposcloner.repo_store — offline, uses tmp_path only."""

import json
import os

import pytest

from reposcloner import repo_store
from reposcloner.repo_store import (
    TrackedRepo,
    dir_name_for,
    discover_local_repos,
    import_repos_txt,
    load_tracked,
    parse_github_id_from_url,
    repo_path_for,
    resolve_work_list,
    save_tracked,
    validate_repo_id,
)


# --- validation -----------------------------------------------------------

@pytest.mark.parametrize('raw,expected', [
    ('owner/repo', 'owner/repo'),
    ('  Owner-1/my.repo_2  ', 'Owner-1/my.repo_2'),
])
def test_validate_repo_id_ok(raw, expected):
    assert validate_repo_id(raw) == expected


@pytest.mark.parametrize('raw', [
    '',
    'just-a-name',
    'owner/repo/extra',
    '../escape',
    '../../etc/passwd',
    '/abs/path',
    'owner\\repo',
    'C:/win/path',
    'owner/',
    '/repo',
    'own er/repo',
])
def test_validate_repo_id_rejects(raw):
    with pytest.raises(ValueError):
        validate_repo_id(raw)


def test_dir_name_for():
    assert dir_name_for('alice/notes') == 'alice__notes'


def test_repo_path_for_prefers_canonical(tmp_path):
    path = repo_path_for(str(tmp_path), 'alice/notes')
    assert path == os.path.join(str(tmp_path), 'alice__notes')


def test_repo_path_for_recognises_legacy(tmp_path):
    legacy = tmp_path / 'alice_notes'
    legacy.mkdir()
    assert repo_path_for(str(tmp_path), 'alice/notes') == str(legacy)


# --- remote URL parsing ----------------------------------------------------

@pytest.mark.parametrize('url,expected', [
    ('https://github.com/alice/notes.git', 'alice/notes'),
    ('https://github.com/alice/notes', 'alice/notes'),
    ('git@github.com:alice/notes.git', 'alice/notes'),
    ('ssh://git@github.com/alice/notes.git', 'alice/notes'),
    ('https://gitlab.com/alice/notes.git', None),
    ('not-a-url', None),
    ('', None),
])
def test_parse_github_id_from_url(url, expected):
    assert parse_github_id_from_url(url) == expected


# --- tracked list ----------------------------------------------------------

def test_load_tracked_missing_file_returns_empty(tmp_path):
    assert load_tracked(str(tmp_path / 'repos.json')) == []


def test_save_and_load_tracked_roundtrip(tmp_path):
    path = str(tmp_path / 'repos.json')
    entries = [TrackedRepo(id='a/one', group='g1'), TrackedRepo(id='b/two', enabled=False)]
    save_tracked(path, entries)
    loaded = load_tracked(path)
    assert [(e.id, e.group, e.enabled) for e in loaded] == [
        ('a/one', 'g1', True), ('b/two', 'default', False)]


def test_load_tracked_plain_list_and_strings(tmp_path):
    path = tmp_path / 'repos.json'
    path.write_text(json.dumps(['a/one', {'id': 'b/two', 'group': 'x'}]), encoding='utf-8')
    loaded = load_tracked(str(path))
    assert [e.id for e in loaded] == ['a/one', 'b/two']
    assert loaded[1].group == 'x'


def test_load_tracked_invalid_json_raises(tmp_path):
    path = tmp_path / 'repos.json'
    path.write_text('{not json', encoding='utf-8')
    with pytest.raises(ValueError):
        load_tracked(str(path))


def test_tracked_repo_validates_id():
    with pytest.raises(ValueError):
        TrackedRepo(id='../evil')


def test_import_repos_txt_skips_bad_lines(tmp_path):
    txt = tmp_path / 'repos.txt'
    txt.write_text('alice/notes\n\n# comment\n../evil\nbob/stuff\n', encoding='utf-8')
    entries = import_repos_txt(str(txt))
    assert [e.id for e in entries] == ['alice/notes', 'bob/stuff']


# --- discovery -------------------------------------------------------------

def _make_checkout(base, dirname, remote_url=None, monkeypatch=None):
    path = base / dirname
    (path / '.git').mkdir(parents=True)
    if monkeypatch is not None:
        monkeypatch.setattr(
            repo_store, '_remote_url_for',
            lambda p: remote_url if os.path.basename(p) == dirname else None,
        )
    return path


def test_discover_finds_checkouts_new_scheme(tmp_path, monkeypatch):
    _make_checkout(tmp_path, 'alice__notes', 'https://github.com/alice/notes.git', monkeypatch)
    (tmp_path / 'plain-dir').mkdir()  # no .git -> ignored
    (tmp_path / 'file.txt').write_text('x', encoding='utf-8')  # ignored
    found = discover_local_repos(str(tmp_path))
    assert len(found) == 1
    assert found[0].repo_id == 'alice/notes'
    assert found[0].remote_url == 'https://github.com/alice/notes.git'


def test_discover_falls_back_to_dir_name(tmp_path, monkeypatch):
    _make_checkout(tmp_path, 'alice__notes', None, monkeypatch)
    found = discover_local_repos(str(tmp_path))
    assert found[0].repo_id == 'alice/notes'


def test_discover_missing_dir_returns_empty(tmp_path):
    assert discover_local_repos(str(tmp_path / 'nope')) == []


# --- work list merge -------------------------------------------------------

def test_resolve_work_list_merges_tracked_and_discovered(tmp_path, monkeypatch):
    _make_checkout(tmp_path, 'alice__notes', 'https://github.com/alice/notes.git', monkeypatch)
    tracked = [TrackedRepo(id='alice/notes', group='class-a', enabled=False),
               TrackedRepo(id='bob/todo')]
    items = resolve_work_list(str(tmp_path), tracked)
    by_id = {i.repo_id: i for i in items}
    assert set(by_id) == {'alice/notes', 'bob/todo'}
    assert by_id['alice/notes'].cloned is True
    assert by_id['alice/notes'].group == 'class-a'
    assert by_id['alice/notes'].enabled is False
    assert by_id['bob/todo'].cloned is False
