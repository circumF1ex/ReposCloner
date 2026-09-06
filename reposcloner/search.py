"""Search and filtering functionality for ReposCloner"""

import os
import re
from typing import List, Dict, Optional
from git import Repo
import logging

from .repo_store import repo_path_for, validate_repo_id

logger = logging.getLogger(__name__)

# Fallback for callers that still rely on init_search (legacy CLI path).
REPOS_DIR = None


def init_search(repos_dir: str):
    """Initialize search module with configuration (legacy; prefer explicit repos_dir)."""
    global REPOS_DIR
    REPOS_DIR = repos_dir


def _resolve_dir(repos_dir: Optional[str], repo_name: str) -> str:
    base = repos_dir or REPOS_DIR
    if not base:
        raise ValueError("repos_dir is not set: pass it explicitly or call init_search()")
    validate_repo_id(repo_name)
    return repo_path_for(base, repo_name)


def filter_repos(repos: List[str], pattern: str) -> List[str]:
    """Filter repositories by name pattern"""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
        filtered = [repo for repo in repos if regex.search(repo)]
        logger.info(f"Filtered {len(filtered)} repositories matching pattern '{pattern}'")
        return filtered
    except re.error as e:
        logger.error(f"Invalid regex pattern: {e}")
        print(f"Invalid pattern: {e}")
        return repos


def search_in_repos(
    query: str,
    repos: List[str],
    repos_dir: Optional[str] = None,
    max_commits: int = 100,
) -> List[Dict]:
    """Search for text in commit messages across all repositories"""
    results = []
    query_lower = query.lower()

    for repo_name in repos:
        try:
            repo_path = _resolve_dir(repos_dir, repo_name)
        except ValueError:
            continue
        if not os.path.exists(repo_path):
            continue

        try:
            repo = Repo(repo_path)
            matches = []
            for commit in repo.iter_commits(max_count=max_commits):
                if query_lower in commit.message.lower():
                    matches.append({
                        'hash': commit.hexsha[:7],
                        'date': commit.authored_datetime.isoformat(),
                        'author': commit.author.name,
                        'message': commit.message.strip()[:100]
                    })

            if matches:
                results.append({
                    'repo': repo_name,
                    'matches': matches,
                    'count': len(matches)
                })
        except Exception as e:
            logger.debug(f"Error searching in {repo_name}: {e}")

    return results
