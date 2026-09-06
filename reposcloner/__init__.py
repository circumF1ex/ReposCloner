"""
ReposCloner - A tool for cloning and managing multiple GitHub repositories
"""

__version__ = '1.1.0'

from .config import load_config, setup_logging
from .git_operations import clone_repo, update_repo, reclone_repo, get_last_commit_summary, view_commit_history
from .utils import load_repos, print_summary, print_progress
from .search import filter_repos, search_in_repos
from .repo_store import (
    TrackedRepo,
    LocalRepo,
    WorkItem,
    validate_repo_id,
    dir_name_for,
    repo_path_for,
    load_tracked,
    save_tracked,
    import_repos_txt,
    discover_local_repos,
    resolve_work_list,
)

__all__ = [
    'load_config',
    'setup_logging',
    'clone_repo',
    'update_repo',
    'reclone_repo',
    'get_last_commit_summary',
    'view_commit_history',
    'load_repos',
    'print_summary',
    'print_progress',
    'filter_repos',
    'search_in_repos',
    'TrackedRepo',
    'LocalRepo',
    'WorkItem',
    'validate_repo_id',
    'dir_name_for',
    'repo_path_for',
    'load_tracked',
    'save_tracked',
    'import_repos_txt',
    'discover_local_repos',
    'resolve_work_list',
]
