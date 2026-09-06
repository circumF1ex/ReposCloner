"""Tests for reposcloner.report — pure function, no git involved."""

from reposcloner.report import build_dashboard_html


def _sample():
    items = [
        {'repo_id': 'alice/notes', 'group': 'class-a', 'cloned': True, 'enabled': True},
        {'repo_id': 'bob/todo', 'group': 'default', 'cloned': False, 'enabled': True},
    ]
    summaries = [
        {'repo': 'alice/notes',
         'last_commit': {'hash': 'deadbeef123', 'message': 'Lecture 5',
                         'author': 'Ann', 'date': '2026-01-02T03:04:00'}},
        {'repo': 'bob/todo', 'status': 'not_cloned'},
    ]
    stats = {'total': 2, 'cloned': 1, 'total_commits': 42, 'total_size_mb': 1.5}
    return items, summaries, stats


def test_dashboard_contains_repos_and_stats():
    items, summaries, stats = _sample()
    page = build_dashboard_html(items, summaries, stats, generated_at='2026-09-07 12:00')
    assert 'alice/notes' in page
    assert 'bob/todo' in page
    assert 'Total repositories: 2' in page
    assert 'Total commits: 42' in page
    assert 'deadbee' in page  # short hash
    assert 'not cloned' in page
    assert '2026-09-07 12:00' in page


def test_dashboard_escapes_html():
    items = [{'repo_id': 'a/b', 'group': 'g', 'cloned': True, 'enabled': True}]
    summaries = [{'repo': 'a/b',
                  'last_commit': {'hash': 'abc', 'message': '<script>alert(1)</script>',
                                  'author': 'x', 'date': '2026-01-01T00:00:00'}}]
    page = build_dashboard_html(items, summaries, {'total': 1})
    assert '<script>' not in page
    assert '&lt;script&gt;' in page


def test_dashboard_empty_inventory():
    page = build_dashboard_html([], [], {})
    assert 'Repositories (0)' in page
