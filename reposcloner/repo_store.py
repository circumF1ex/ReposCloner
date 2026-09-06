"""Repository inventory: local discovery + tracked list (replaces repos.txt).

Two sources, merged at runtime:

- **Discovery (primary):** any subdirectory of ``repos_dir`` containing a
  ``.git`` folder is a known repository. The canonical ``owner/repo`` id is
  resolved from the git remote URL when available, falling back to the
  directory name.
- **Tracked list (secondary):** ``repos.json`` remembers repositories you
  *want* but have not cloned yet, plus per-repo metadata (group,
  enabled flag). This is the only file the user ever edits — and normally
  only through the GUI.

Directory naming
----------------
New clones use ``{owner}__{repo}`` (double underscore). The legacy scheme
``{owner}_{repo}`` (single underscore) is still recognised on read so
existing checkouts keep working.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

#: Strict ``owner/repo`` shape. Rejects ``..``, slashes, backslashes,
#: drive letters and anything that could escape ``repos_dir``.
REPO_ID_RE = re.compile(r'^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)$')

LEGACY_SEPARATOR = '_'
DIR_SEPARATOR = '__'

TRACKED_FILENAME = 'repos.json'


# ---------------------------------------------------------------------------
# Validation / naming
# ---------------------------------------------------------------------------

def validate_repo_id(value: str) -> str:
    """Normalize and validate an ``owner/repo`` identifier.

    Raises:
        ValueError: if the value is not a safe ``owner/repo`` id.
    """
    cleaned = (value or '').strip()
    match = REPO_ID_RE.match(cleaned)
    if not match:
        raise ValueError(
            f"Invalid repository id {value!r}: expected 'owner/repo' "
            "using letters, digits, '.', '-' or '_'."
        )
    owner, repo = match.group('owner'), match.group('repo')
    if owner in ('.', '..') or repo in ('.', '..'):
        raise ValueError(
            f"Invalid repository id {value!r}: '.' and '..' are not allowed."
        )
    return f"{owner}/{repo}"


def dir_name_for(repo_id: str) -> str:
    """Canonical on-disk directory name for a repository id."""
    repo_id = validate_repo_id(repo_id)
    owner, repo = repo_id.split('/')
    return f"{owner}{DIR_SEPARATOR}{repo}"


def repo_path_for(repos_dir: str, repo_id: str) -> str:
    """Absolute path of the checkout, recognising legacy names.

    Returns the legacy ``owner_repo`` path if that directory already exists
    (backward compatibility), otherwise the canonical path.
    """
    repo_id = validate_repo_id(repo_id)
    canonical = os.path.join(repos_dir, dir_name_for(repo_id))
    if os.path.isdir(canonical):
        return canonical
    owner, repo = repo_id.split('/')
    legacy = os.path.join(repos_dir, f"{owner}{LEGACY_SEPARATOR}{repo}")
    if os.path.isdir(legacy):
        return legacy
    return canonical


def parse_github_id_from_url(url: str) -> Optional[str]:
    """Extract ``owner/repo`` from a git remote URL, or None."""
    if not url:
        return None
    cleaned = url.strip().rstrip('/')
    if cleaned.endswith('.git'):
        cleaned = cleaned[:-4]
    # https://github.com/owner/repo , git@github.com:owner/repo , ssh variants
    match = re.search(r'github\.com[/:]([^/]+)/([^/]+)$', cleaned, re.IGNORECASE)
    if not match:
        return None
    try:
        return validate_repo_id(f"{match.group(1)}/{match.group(2)}")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Tracked list (repos.json)
# ---------------------------------------------------------------------------

@dataclass
class TrackedRepo:
    id: str
    group: str = 'default'
    enabled: bool = True

    def __post_init__(self) -> None:
        self.id = validate_repo_id(self.id)


def default_tracked_path(repos_dir: str) -> str:
    return os.path.join(repos_dir, TRACKED_FILENAME)


def load_tracked(path: str) -> List[TrackedRepo]:
    """Load the tracked list. Missing file → empty list (not an error)."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error reading tracked repos file {path}: {e}")
        raise ValueError(f"Cannot read tracked repos file {path}: {e}") from e
    items = raw.get('repositories', raw) if isinstance(raw, dict) else raw
    entries: List[TrackedRepo] = []
    for item in items:
        if isinstance(item, str):
            entries.append(TrackedRepo(id=item))
        elif isinstance(item, dict) and 'id' in item:
            entries.append(TrackedRepo(
                id=item['id'],
                group=item.get('group', 'default'),
                enabled=item.get('enabled', True),
            ))
        else:
            logger.warning(f"Skipping invalid tracked entry: {item!r}")
    return entries


def save_tracked(path: str, entries: List[TrackedRepo]) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    payload = {'version': 1, 'repositories': [asdict(e) for e in entries]}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def import_repos_txt(txt_path: str) -> List[TrackedRepo]:
    """One-time migration helper: parse legacy repos.txt (skips bad lines)."""
    entries: List[TrackedRepo] = []
    with open(txt_path, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            try:
                entries.append(TrackedRepo(id=line))
            except ValueError:
                logger.warning(f"{txt_path}:{lineno}: skipping invalid id {line!r}")
    return entries


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@dataclass
class LocalRepo:
    """A checkout actually present on disk."""
    dir_name: str
    path: str
    repo_id: Optional[str] = None
    remote_url: Optional[str] = None
    cloned: bool = True


def _remote_url_for(path: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=path, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _id_from_dir_name(dir_name: str) -> Optional[str]:
    if DIR_SEPARATOR in dir_name:
        owner, _, repo = dir_name.partition(DIR_SEPARATOR)
        candidate = f"{owner}/{repo}"
    elif LEGACY_SEPARATOR in dir_name:
        # Ambiguous for owners containing '_'; best effort only.
        owner, _, repo = dir_name.partition(LEGACY_SEPARATOR)
        candidate = f"{owner}/{repo}"
    else:
        return None
    try:
        return validate_repo_id(candidate)
    except ValueError:
        return None


def discover_local_repos(repos_dir: str) -> List[LocalRepo]:
    """Scan ``repos_dir`` for checkouts (dirs containing ``.git``)."""
    found: List[LocalRepo] = []
    if not os.path.isdir(repos_dir):
        return found
    for dir_name in sorted(os.listdir(repos_dir)):
        path = os.path.join(repos_dir, dir_name)
        if not os.path.isdir(path):
            continue
        if not os.path.isdir(os.path.join(path, '.git')):
            continue
        remote_url = _remote_url_for(path)
        repo_id = parse_github_id_from_url(remote_url or '') or _id_from_dir_name(dir_name)
        found.append(LocalRepo(
            dir_name=dir_name,
            path=path,
            repo_id=repo_id,
            remote_url=remote_url,
        ))
    return found


@dataclass
class WorkItem:
    """One row for the UI / batch operations."""
    repo_id: str
    path: str
    cloned: bool
    group: str = 'default'
    enabled: bool = True
    remote_url: Optional[str] = None


def resolve_work_list(
    repos_dir: str,
    tracked: List[TrackedRepo],
    discovered: Optional[List[LocalRepo]] = None,
) -> List[WorkItem]:
    """Merge tracked + discovered into a single de-duplicated work list."""
    discovered = discovered if discovered is not None else discover_local_repos(repos_dir)
    by_id: Dict[str, WorkItem] = {}
    by_dir: Dict[str, WorkItem] = {}

    for local in discovered:
        key = local.repo_id or f"local:{local.dir_name}"
        item = WorkItem(
            repo_id=local.repo_id or local.dir_name,
            path=local.path,
            cloned=True,
            remote_url=local.remote_url,
        )
        by_id[key] = item
        by_dir[local.dir_name] = item

    for entry in tracked:
        if entry.id in by_id:
            by_id[entry.id].group = entry.group
            by_id[entry.id].enabled = entry.enabled
            continue
        by_id[entry.id] = WorkItem(
            repo_id=entry.id,
            path=repo_path_for(repos_dir, entry.id),
            cloned=os.path.isdir(repo_path_for(repos_dir, entry.id)),
            group=entry.group,
            enabled=entry.enabled,
        )
    return [by_id[k] for k in sorted(by_id)]
