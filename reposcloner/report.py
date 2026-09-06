"""Standalone HTML dashboard export (no server needed).

:func:`build_dashboard_html` is a pure function: it takes plain data and
returns a self-contained HTML string. It is used by the "Export HTML"
button of the web UI and is fully unit-testable.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Dict, List


def _esc(value) -> str:
    return html.escape(str(value) if value is not None else '')


def build_dashboard_html(
    items: List[Dict],
    summaries: List[Dict],
    stats: Dict,
    generated_at: str = '',
) -> str:
    """Build a standalone status page.

    Args:
        items: list of ``{'repo_id', 'group', 'cloned', 'enabled'}`` dicts.
        summaries: list of ``get_last_commit_summary``-shaped dicts.
        stats: dict with ``total``, ``cloned``, ``total_commits``,
            ``total_size_mb`` keys.
        generated_at: display string; defaults to now.
    """
    generated_at = generated_at or datetime.now().strftime('%Y-%m-%d %H:%M')
    last_by_repo = {s.get('repo'): s for s in summaries}

    rows = []
    for item in items:
        repo_id = item.get('repo_id', '?')
        summary = last_by_repo.get(repo_id, {})
        commit = summary.get('last_commit', {})
        if commit:
            last_info = f"{_esc(commit.get('hash', '')[:7])} — {_esc(commit.get('message', '')[:80])}"
        elif summary.get('status') == 'not_cloned':
            last_info = '<em>not cloned</em>'
        else:
            last_info = '<em>n/a</em>'
        cloned = 'yes' if item.get('cloned') else 'no'
        rows.append(
            f"<tr><td>{_esc(repo_id)}</td><td>{_esc(item.get('group', ''))}</td>"
            f"<td>{cloned}</td><td>{last_info}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ReposCloner dashboard</title>
<style>
body {{ font-family: sans-serif; margin: 2em; color: #222; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
th {{ background: #f0f0f0; }}
.stats li {{ margin: 2px 0; }}
</style>
</head>
<body>
<h1>ReposCloner dashboard</h1>
<p>Generated: {_esc(generated_at)}</p>
<h2>Statistics</h2>
<ul class="stats">
<li>Total repositories: {_esc(stats.get('total', 0))}</li>
<li>Cloned: {_esc(stats.get('cloned', 0))}</li>
<li>Total commits: {_esc(stats.get('total_commits', 0))}</li>
<li>Total size: {_esc(stats.get('total_size_mb', 0))} MB</li>
</ul>
<h2>Repositories ({len(rows)})</h2>
<table>
<tr><th>Repository</th><th>Group</th><th>Cloned</th><th>Last commit</th></tr>
{''.join(rows)}
</table>
</body>
</html>
"""
