"""Tests for reposcloner.git_operations — git is fully mocked, no network."""

import os

import pytest
from git import GitCommandError

from reposcloner import git_operations


# --- fakes -----------------------------------------------------------------

class FakeAuthor:
    def __init__(self, name='Author'):
        self.name = name


class FakeCommit:
    def __init__(self, hexsha='abc123', message='msg', author='Author'):
        from datetime import datetime, timezone
        self.hexsha = hexsha
        self.message = message
        self.author = FakeAuthor(author)
        self.authored_datetime = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)


class FakeGit:
    def __init__(self, repo):
        self.repo = repo
        self.calls = []

    def config(self, *args):
        self.calls.append(('config', args))

    def fetch(self):
        self.calls.append(('fetch', ()))

    def reset(self, *args):
        self.calls.append(('reset', args))
        if self.repo.reset_side_effect is not None:
            raise self.repo.reset_side_effect


class FakeOrigin:
    def __init__(self, pull_side_effect=None):
        self.pull_side_effect = pull_side_effect
        self.pulled = False

    def pull(self):
        self.pulled = True
        if self.pull_side_effect is not None:
            raise self.pull_side_effect


class FakeHead:
    def __init__(self, commit):
        self.commit = commit


class FakeRepo:
    """Stand-in for git.Repo. Configure via class attributes per test."""

    instances = []
    clone_from_side_effect = None

    def __init__(self, path):
        self.path = path
        self.active_branch = type('Branch', (), {'name': 'main'})()
        self.head = FakeHead(FakeRepo.head_commit)
        self.remotes = type('R', (), {'origin': FakeRepo.origin})()
        self.git = FakeGit(self)
        self.commits_range = list(FakeRepo.commits_range)
        self.reset_side_effect = None
        FakeRepo.instances.append(self)

    @classmethod
    def clone_from(cls, url, path, **kwargs):
        cls.clone_calls.append({'url': url, 'path': path, **kwargs})
        if cls.clone_from_side_effect is not None:
            raise cls.clone_from_side_effect
        os.makedirs(path, exist_ok=True)
        return cls(path)

    def iter_commits(self, *args, **kwargs):
        return iter(self.commits_range)


@pytest.fixture(autouse=True)
def fake_repo(monkeypatch):
    FakeRepo.instances = []
    FakeRepo.clone_calls = []
    FakeRepo.clone_from_side_effect = None
    FakeRepo.head_commit = FakeCommit(hexsha='aaa')
    FakeRepo.commits_range = []
    FakeRepo.origin = FakeOrigin()
    monkeypatch.setattr(git_operations, 'Repo', FakeRepo)
    monkeypatch.setattr(git_operations, 'MAX_RETRIES', 0)
    return FakeRepo


@pytest.fixture()
def repos_dir(tmp_path):
    d = tmp_path / 'repos'
    d.mkdir()
    return str(d)


def _checkout(repos_dir, repo_id, scheme='__'):
    owner, repo = repo_id.split('/')
    path = os.path.join(repos_dir, f'{owner}{scheme}{repo}')
    os.makedirs(os.path.join(path, '.git'))
    return path


# --- clone -----------------------------------------------------------------

def test_clone_invalid_id_returns_error(repos_dir):
    result = git_operations.clone_repo('../evil', repos_dir=repos_dir)
    assert result['status'] == 'error'


def test_clone_already_cloned(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    assert git_operations.clone_repo('alice/notes', repos_dir=repos_dir)['status'] == 'already_cloned'


def test_clone_success(repos_dir):
    result = git_operations.clone_repo('alice/notes', repos_dir=repos_dir)
    assert result == {'repo': 'alice/notes', 'status': 'cloned'}


def test_clone_forwards_depth(repos_dir):
    result = git_operations.clone_repo('alice/notes', repos_dir=repos_dir, depth=1)
    assert result['status'] == 'cloned'
    assert FakeRepo.clone_calls[-1]['depth'] == 1
    assert FakeRepo.clone_calls[-1]['url'] == 'https://github.com/alice/notes.git'


def test_clone_failure_returns_error(repos_dir):
    FakeRepo.clone_from_side_effect = GitCommandError('clone', 'boom')
    result = git_operations.clone_repo('alice/notes', repos_dir=repos_dir)
    assert result['status'] == 'error'
    assert 'boom' in result['message']


# --- update ----------------------------------------------------------------

def test_update_not_cloned(repos_dir):
    assert git_operations.update_repo('alice/notes', repos_dir=repos_dir)['status'] == 'not_cloned'


def test_update_no_changes(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    result = git_operations.update_repo('alice/notes', repos_dir=repos_dir)
    assert result['status'] == 'no_changes'


def test_update_conflict_by_default_keeps_worktree(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    FakeRepo.origin = FakeOrigin(pull_side_effect=GitCommandError('pull', 'conflict!'))
    result = git_operations.update_repo('alice/notes', repos_dir=repos_dir)
    assert result['status'] == 'conflict'
    repo = FakeRepo.instances[-1]
    assert repo.git.calls == []  # no fetch/reset happened


def test_update_force_discards_changes(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    FakeRepo.origin = FakeOrigin(pull_side_effect=GitCommandError('pull', 'conflict!'))
    FakeRepo.head_commit = FakeCommit(hexsha='aaa')
    result = git_operations.update_repo('alice/notes', repos_dir=repos_dir, force=True)
    # old == new here (fake head never moves) -> no_changes, but the
    # destructive path must have been taken:
    assert result['status'] == 'no_changes'
    repo = FakeRepo.instances[-1]
    assert ('fetch', ()) in repo.git.calls
    assert any(call[0] == 'reset' for call in repo.git.calls)


def test_update_force_reports_new_commits(repos_dir, monkeypatch):
    _checkout(repos_dir, 'alice/notes')
    FakeRepo.origin = FakeOrigin(pull_side_effect=GitCommandError('pull', 'conflict!'))

    new_head = FakeCommit(hexsha='zzz', message='new stuff', author='Bob')
    commits = [FakeCommit(hexsha='zzz', message='new stuff', author='Bob')]

    def fake_reset(self, *args):
        self.repo.head = FakeHead(new_head)
        self.calls.append(('reset', args))

    monkeypatch.setattr(FakeGit, 'reset', fake_reset)
    FakeRepo.commits_range = commits
    result = git_operations.update_repo('alice/notes', repos_dir=repos_dir, force=True)
    assert result['status'] == 'updated_forced'
    assert result['new_commits_count'] == 1
    assert result['new_commits'][0]['author'] == 'Bob'


# --- history -----------------------------------------------------------------

def test_commit_history_not_cloned(repos_dir):
    result = git_operations.get_commit_history('a/b', repos_dir=repos_dir)
    assert result['status'] == 'not_cloned'
    assert result['commits'] == []


def test_commit_history_ok_with_limit(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    FakeRepo.commits_range = [
        FakeCommit(hexsha='111', message='first'),
        FakeCommit(hexsha='222', message='second'),
    ]
    result = git_operations.get_commit_history('alice/notes', limit=10, repos_dir=repos_dir)
    assert result['status'] == 'ok'
    assert result['count'] == 2
    assert result['commits'][0]['short_hash'] == '111'
    assert result['commits'][1]['message'] == 'second'


def test_commit_history_invalid_id(repos_dir):
    assert git_operations.get_commit_history('../x', repos_dir=repos_dir)['status'] == 'error'


# --- delete ------------------------------------------------------------------

def test_delete_not_cloned(repos_dir):
    assert git_operations.delete_repo_checkout('a/b', repos_dir=repos_dir)['status'] == 'not_cloned'


def test_delete_invalid_id(repos_dir):
    assert git_operations.delete_repo_checkout('../x', repos_dir=repos_dir)['status'] == 'error'


def test_delete_removes_directory(repos_dir):
    path = _checkout(repos_dir, 'alice/notes')
    with open(os.path.join(path, 'file.txt'), 'w') as f:
        f.write('data')
    result = git_operations.delete_repo_checkout('alice/notes', repos_dir=repos_dir)
    assert result == {'repo': 'alice/notes', 'status': 'deleted'}
    assert not os.path.exists(path)


def test_delete_recognises_legacy_dir(repos_dir):
    path = _checkout(repos_dir, 'alice/notes', scheme='_')
    result = git_operations.delete_repo_checkout('alice/notes', repos_dir=repos_dir)
    assert result['status'] == 'deleted'
    assert not os.path.exists(path)


# --- summaries --------------------------------------------------------------

def test_last_commit_summary_not_cloned(repos_dir):
    assert git_operations.get_last_commit_summary('a/b', repos_dir=repos_dir)['status'] == 'not_cloned'


def test_last_commit_summary_ok(repos_dir):
    _checkout(repos_dir, 'alice/notes')
    FakeRepo.head_commit = FakeCommit(hexsha='deadbeef', message='hello', author='Ann')
    summary = git_operations.get_last_commit_summary('alice/notes', repos_dir=repos_dir)
    assert summary['last_commit']['hash'] == 'deadbeef'
    assert summary['last_commit']['author'] == 'Ann'


def test_reclone_invalid_id(repos_dir):
    assert git_operations.reclone_repo('..\\evil', repos_dir=repos_dir)['status'] == 'error'
