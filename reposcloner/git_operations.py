"""Git operations for cloning, updating, and managing repositories.

All functions accept an optional ``repos_dir``. When omitted, the value set
via :func:`init_git_operations` is used (kept for backward compatibility
with the CLI; new code — and the future GUI — should pass it explicitly).
"""

import os
import shutil
import time
from git import Repo, GitCommandError
from typing import Dict, Optional
import logging

from .repo_store import repo_path_for, validate_repo_id

logger = logging.getLogger(__name__)

# Fallback for callers that still rely on init_* (legacy CLI path).
REPOS_DIR = None
MAX_RETRIES = 3
RETRY_DELAY = 2


def init_git_operations(repos_dir: str, max_retries: int = 3, retry_delay: int = 2):
    """Initialize module defaults (legacy; prefer passing repos_dir explicitly)."""
    global REPOS_DIR, MAX_RETRIES, RETRY_DELAY
    REPOS_DIR = repos_dir
    MAX_RETRIES = max_retries
    RETRY_DELAY = retry_delay


def _resolve_dir(repos_dir: Optional[str], repo_name: str) -> str:
    base = repos_dir or REPOS_DIR
    if not base:
        raise ValueError("repos_dir is not set: pass it explicitly or call init_git_operations()")
    # Validates the id — rejects '..', absolute paths, backslashes, etc.
    validate_repo_id(repo_name)
    return repo_path_for(base, repo_name)


def clone_repo(
    repo_name: str,
    retry_count: int = 0,
    repos_dir: Optional[str] = None,
    depth: Optional[int] = None,
) -> Dict:
    """Clone a repository from GitHub.

    ``depth=1`` makes a shallow snapshot (fast; history-dependent features
    are limited on such checkouts). Exposed in the UI only in debug mode.
    """
    try:
        repo_path = _resolve_dir(repos_dir, repo_name)
    except ValueError as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}
    if os.path.exists(repo_path):
        logger.debug(f"Repository {repo_name} already cloned")
        return {'repo': repo_name, 'status': 'already_cloned'}
    try:
        logger.info(f"Cloning repository {repo_name}")
        clone_kwargs = {'depth': depth} if depth else {}
        Repo.clone_from(f'https://github.com/{repo_name}.git', repo_path, **clone_kwargs)
        # Configure git settings after cloning
        repo = Repo(repo_path)
        repo.git.config('core.longpaths', 'true')
        repo.git.config('core.quotepath', 'false')
        logger.info(f"Successfully cloned {repo_name}")
        return {'repo': repo_name, 'status': 'cloned'}
    except GitCommandError as e:
        logger.warning(f"Error cloning {repo_name} (attempt {retry_count + 1}): {str(e)}")
        if retry_count < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return clone_repo(repo_name, retry_count + 1, repos_dir, depth)
        logger.error(f"Failed to clone {repo_name} after {MAX_RETRIES} attempts")
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}


def update_repo(repo_name: str, repos_dir: Optional[str] = None, force: bool = False) -> Dict:
    """Pull latest changes.

    On a merge conflict the default is to report ``status: 'conflict'`` and
    leave the working tree untouched. Pass ``force=True`` (after explicit
    user confirmation in the UI) to discard local changes via
    ``fetch + reset --hard``.
    """
    try:
        repo_path = _resolve_dir(repos_dir, repo_name)
    except ValueError as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}
    if not os.path.exists(repo_path):
        return {'repo': repo_name, 'status': 'not_cloned'}
    old_commit = None
    try:
        repo = Repo(repo_path)
        old_commit = repo.head.commit.hexsha
        origin = repo.remotes.origin
        origin.pull()
        new_commit = repo.head.commit.hexsha
        if old_commit != new_commit:
            try:
                new_commits = list(repo.iter_commits(f'{old_commit}..{new_commit}'))
            except Exception:
                # If commit range is invalid, just report update without commit details
                new_commits = []
            changes = {
                'repo': repo_name,
                'status': 'updated',
                'old_commit': old_commit,
                'new_commit': new_commit,
                'new_commits_count': len(new_commits),
                'new_commits': [{'hash': c.hexsha, 'message': c.message.strip(), 'author': c.author.name} for c in new_commits]
            }
        else:
            changes = {'repo': repo_name, 'status': 'no_changes'}
    except GitCommandError as e:
        if not force:
            logger.warning(f"Conflict updating {repo_name}; leaving working tree untouched")
            return {
                'repo': repo_name,
                'status': 'conflict',
                'message': (
                    f"Pull failed ({e}). Local changes were kept. "
                    "Re-run with force=True to discard them."
                ),
            }
        # Explicitly confirmed destructive path: fetch and reset --hard
        try:
            if old_commit is None:
                repo = Repo(repo_path)
                old_commit = repo.head.commit.hexsha
            repo.git.fetch()
            current_branch = repo.active_branch.name
            repo.git.reset('--hard', f'origin/{current_branch}')
            new_commit = repo.head.commit.hexsha
            if old_commit != new_commit:
                try:
                    new_commits = list(repo.iter_commits(f'{old_commit}..{new_commit}'))
                except Exception:
                    # If commit range is invalid, just report update without commit details
                    new_commits = []
                changes = {
                    'repo': repo_name,
                    'status': 'updated_forced',
                    'old_commit': old_commit,
                    'new_commit': new_commit,
                    'new_commits_count': len(new_commits),
                    'new_commits': [{'hash': c.hexsha, 'message': c.message.strip(), 'author': c.author.name} for c in new_commits]
                }
            else:
                changes = {'repo': repo_name, 'status': 'no_changes'}
        except GitCommandError as e2:
            changes = {'repo': repo_name, 'status': 'error', 'message': f"Failed to update: {str(e2)}"}
    except Exception as e:
        changes = {'repo': repo_name, 'status': 'error', 'message': f"Unexpected error: {str(e)}"}
    return changes


def get_last_commit_summary(repo_name: str, repos_dir: Optional[str] = None) -> Dict:
    """Get summary of the last commit in a repository."""
    try:
        repo_path = _resolve_dir(repos_dir, repo_name)
    except ValueError as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}
    if not os.path.exists(repo_path):
        return {'repo': repo_name, 'status': 'not_cloned'}
    try:
        repo = Repo(repo_path)
        commit = repo.head.commit
        summary = {
            'repo': repo_name,
            'last_commit': {
                'hash': commit.hexsha,
                'message': commit.message.strip(),
                'author': commit.author.name,
                'date': commit.authored_datetime.isoformat()
            }
        }
        return summary
    except Exception as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}


def get_commit_history(
    repo_name: str,
    limit: Optional[int] = None,
    repos_dir: Optional[str] = None,
) -> Dict:
    """Return commit history data (list of dicts) for programmatic use."""
    from typing import List  # local import to keep module header stable
    try:
        repo_path = _resolve_dir(repos_dir, repo_name)
    except ValueError as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}
    if not os.path.exists(repo_path):
        return {'repo': repo_name, 'status': 'not_cloned', 'commits': []}
    try:
        repo = Repo(repo_path)
        commits = list(repo.iter_commits(max_count=limit)) if limit else list(repo.iter_commits())
        data: List[Dict] = [{
            'hash': c.hexsha,
            'short_hash': c.hexsha[:7],
            'date': c.authored_datetime.isoformat(),
            'author': c.author.name,
            'message': c.message.strip(),
        } for c in commits]
        return {'repo': repo_name, 'status': 'ok', 'commits': data, 'count': len(data)}
    except Exception as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e), 'commits': []}


def view_commit_history(repo_name: str, limit: Optional[int] = None, repos_dir: Optional[str] = None):
    """View commit history for a repository."""
    try:
        repo_path = _resolve_dir(repos_dir, repo_name)
    except ValueError as e:
        print(f"Invalid repository id: {e}")
        return
    if not os.path.exists(repo_path):
        print(f"Repository {repo_name} not cloned.")
        return
    try:
        repo = Repo(repo_path)
        commits = list(repo.iter_commits(max_count=limit)) if limit else list(repo.iter_commits())
        if commits:
            print(f"\nCommit history for {repo_name} ({len(commits)} commits):")
            print("-" * 80)
            for i, commit in enumerate(commits, 1):
                date = commit.authored_datetime.strftime('%Y-%m-%d %H:%M')
                message = commit.message.strip().split('\n')[0]  # First line only
                print(f"{i:3d}. {commit.hexsha[:7]} | {date} | {commit.author.name:20s} | {message[:50]}")
            print("-" * 80)
        else:
            print(f"No commits in {repo_name}.")
    except Exception as e:
        print(f"Error viewing history: {str(e)}")


def delete_repo_checkout(repo_name: str, repos_dir: Optional[str] = None) -> Dict:
    """Delete the local checkout directory (tracked entry is left alone).

    Returns ``status: 'deleted'`` / ``'not_cloned'`` / ``'error'``.
    """
    try:
        repo_path = _resolve_dir(repos_dir, repo_name)
    except ValueError as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}
    if not os.path.exists(repo_path):
        return {'repo': repo_name, 'status': 'not_cloned'}
    try:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                shutil.rmtree(repo_path)
                break
            except OSError as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise e
        logger.info(f"Deleted local checkout {repo_name}")
        return {'repo': repo_name, 'status': 'deleted'}
    except Exception as e:
        if 'WinError 5' in str(e) or 'Access denied' in str(e):
            message = (f"Access denied while deleting '{repo_path}'. Close file explorers, "
                       f"Git GUIs or antivirus locks and try again. Original error: {e}")
        else:
            message = str(e)
        return {'repo': repo_name, 'status': 'error', 'message': message}


def reclone_repo(repo_name: str, repos_dir: Optional[str] = None) -> Dict:
    """Reclone a repository (delete and clone again)."""
    try:
        repo_path = _resolve_dir(repos_dir, repo_name)
    except ValueError as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}
    try:
        if os.path.exists(repo_path):
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    shutil.rmtree(repo_path)
                    break
                except OSError as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        raise e
        Repo.clone_from(f'https://github.com/{repo_name}.git', repo_path)
        # Configure git settings after cloning
        repo = Repo(repo_path)
        repo.git.config('core.longpaths', 'true')
        repo.git.config('core.quotepath', 'false')
        return {'repo': repo_name, 'status': 'recloned'}
    except Exception as e:
        if 'WinError 5' in str(e) or 'Access denied' in str(e):
            message = f"Access denied while deleting repository directory. Please ensure no other processes are using the files (e.g., close Git GUI, file explorer, or antivirus). You may need to manually delete the folder '{repo_path}' and try again. Original error: {str(e)}"
        else:
            message = str(e)
        return {'repo': repo_name, 'status': 'error', 'message': message}
