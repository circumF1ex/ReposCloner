"""Tests for reposcloner.search — git is fully mocked."""

import os
from datetime import datetime, timezone

import pytest

from reposcloner import search as search_module
from reposcloner.search import filter_repos, search_in_repos


def test_filter_repos_basic():
    repos = ['alice/notes', 'bob/RPO-stuff', 'carol/konspekt']
    assert filter_repos(repos, 'rpo') == ['bob/RPO-stuff']
    assert filter_repos(repos, '^(alice|carol)') == ['alice/notes', 'carol/konspekt']


def test_filter_repos_invalid_regex_returns_original():
    repos = ['a/b']
    assert filter_repos(repos, '([') == repos


class FakeAuthor:
    def __init__(self, name):
        self.name = name


class FakeCommit:
    def __init__(self, message, author='Ann', hexsha='abc1234'):
        self.message = message
        self.author = FakeAuthor(author)
        self.hexsha = hexsha
        self.authored_datetime = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)


class FakeRepo:
    commits = []

    def __init__(self, path):
        self.path = path

    def iter_commits(self, max_count=None):
        return iter(FakeRepo.commits[:max_count] if max_count else FakeRepo.commits)


@pytest.fixture()
def repos_dir(tmp_path, monkeypatch):
    d = tmp_path / 'repos'
    d.mkdir()
    monkeypatch.setattr(search_module, 'Repo', FakeRepo)
    return str(d)


def _checkout(repos_dir, repo_id):
    owner, repo = repo_id.split('/')
    path = os.path.join(repos_dir, f'{owner}__{repo}')
    os.makedirs(os.path.join(path, '.git'))
    return path


def test_search_finds_matches(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    FakeRepo.commits = [FakeCommit('Lecture 5: integrals'), FakeCommit('homework fix')]
    results = search_in_repos('lecture', ['alice/notes'], repos_dir=repos_dir)
    assert len(results) == 1
    assert results[0]['count'] == 1
    assert 'integrals' in results[0]['matches'][0]['message']


def test_search_skips_missing_and_invalid(repos_dir):
    FakeRepo.commits = [FakeCommit('lecture notes')]
    results = search_in_repos('lecture', ['ghost/repo', '../evil'], repos_dir=repos_dir)
    assert results == []


def test_search_no_match_returns_empty(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    FakeRepo.commits = [FakeCommit('totally unrelated')]
    assert search_in_repos('lecture', ['alice/notes'], repos_dir=repos_dir) == []
