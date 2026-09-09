"""
ReposCloner - A tool for cloning and managing multiple GitHub repositories
"""

__version__ = '1.2.0'

from .config import is_debug_enabled, load_config, save_config, setup_logging
from .i18n import DEFAULT_LANGUAGE, AVAILABLE_LANGUAGES, get_lang, t
from .git_operations import clone_repo, update_repo, reclone_repo, delete_repo_checkout, get_last_commit_summary, get_commit_history, view_commit_history
from .report import build_dashboard_html
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
    'is_debug_enabled',
    'load_config',
    'save_config',
    'setup_logging',
    'DEFAULT_LANGUAGE',
    'AVAILABLE_LANGUAGES',
    'get_lang',
    't',
    'clone_repo',
    'update_repo',
    'reclone_repo',
    'delete_repo_checkout',
    'get_last_commit_summary',
    'get_commit_history',
    'view_commit_history',
    'build_dashboard_html',
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
