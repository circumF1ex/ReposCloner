"""Search and filtering functionality for ReposCloner"""

import os
import re
from typing import List, Dict
from git import Repo
import logging

logger = logging.getLogger(__name__)

# This will be set by the main module
REPOS_DIR = None

def init_search(repos_dir: str):
    """Initialize search module with configuration"""
    global REPOS_DIR
    REPOS_DIR = repos_dir

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

def search_in_repos(query: str, repos: List[str]) -> List[Dict]:
    """Search for text in commit messages across all repositories"""
    results = []
    query_lower = query.lower()
    
    for repo_name in repos:
        repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
        if not os.path.exists(repo_path):
            continue
        
        try:
            repo = Repo(repo_path)
            matches = []
            for commit in repo.iter_commits(max_count=100):  # Limit search to recent commits
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
