"""Utility functions for ReposCloner"""

import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def load_repos(repos_file: str) -> List[str]:
    """Load repositories from file"""
    try:
        with open(repos_file, 'r', encoding='utf-8') as f:
            repos = [line.strip() for line in f if line.strip()]
        if not repos:
            logger.warning(f"{repos_file} is empty.")
            print(f"Warning: {repos_file} is empty.")
        else:
            logger.info(f"Loaded {len(repos)} repositories from {repos_file}")
        return repos
    except FileNotFoundError:
        logger.error(f"{repos_file} not found.")
        print(f"Error: {repos_file} not found.")
        return []
    except Exception as e:
        logger.error(f"Error reading {repos_file}: {str(e)}")
        print(f"Error reading {repos_file}: {str(e)}")
        return []

def print_summary(results: List[Dict], operation: str):
    """Print summary statistics after batch operations"""
    total = len(results)
    success = sum(1 for r in results if r.get('status') in ['cloned', 'updated', 'updated_forced', 'recloned', 'already_cloned', 'no_changes'])
    errors = sum(1 for r in results if r.get('status') == 'error')
    updated = sum(1 for r in results if r.get('status') in ['updated', 'updated_forced'])
    new_commits_total = sum(r.get('new_commits_count', 0) for r in results if 'new_commits_count' in r)
    
    print("\n" + "="*60)
    print(f"SUMMARY - {operation.upper()}")
    print("="*60)
    print(f"Total repositories: {total}")
    print(f"Successful: {success}")
    print(f"Errors: {errors}")
    if operation == "update":
        print(f"Updated: {updated}")
        print(f"Total new commits: {new_commits_total}")
    print("="*60 + "\n")
    
    if errors > 0:
        print("Errors encountered:")
        for r in results:
            if r.get('status') == 'error':
                print(f"  - {r['repo']}: {r.get('message', 'Unknown error')}")

def print_progress(current: int, total: int, repo_name: str, status: str = ""):
    """Print progress indicator"""
    percentage = (current / total) * 100
    bar_length = 30
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    status_text = f" - {status}" if status else ""
    print(f"\r[{bar}] {percentage:.1f}% ({current}/{total}) - {repo_name}{status_text}", end='', flush=True)
