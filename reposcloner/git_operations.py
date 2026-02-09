"""Git operations for cloning, updating, and managing repositories"""

import os
import shutil
import time
from git import Repo, GitCommandError
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# These will be set by the main module
REPOS_DIR = None
MAX_RETRIES = 3
RETRY_DELAY = 2

def init_git_operations(repos_dir: str, max_retries: int = 3, retry_delay: int = 2):
    """Initialize git operations module with configuration"""
    global REPOS_DIR, MAX_RETRIES, RETRY_DELAY
    REPOS_DIR = repos_dir
    MAX_RETRIES = max_retries
    RETRY_DELAY = retry_delay

def clone_repo(repo_name: str, retry_count: int = 0) -> Dict:
    """Clone a repository from GitHub"""
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
    if os.path.exists(repo_path):
        logger.debug(f"Repository {repo_name} already cloned")
        return {'repo': repo_name, 'status': 'already_cloned'}
    try:
        logger.info(f"Cloning repository {repo_name}")
        Repo.clone_from(f'https://github.com/{repo_name}.git', repo_path)
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
            return clone_repo(repo_name, retry_count + 1)
        logger.error(f"Failed to clone {repo_name} after {MAX_RETRIES} attempts")
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}

def update_repo(repo_name: str) -> Dict:
    """Update a repository by pulling latest changes"""
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
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
        # Merge/overwrite by default: fetch and reset --hard
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

def get_last_commit_summary(repo_name: str) -> Dict:
    """Get summary of the last commit in a repository"""
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
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

def view_commit_history(repo_name: str, limit: Optional[int] = None):
    """View commit history for a repository"""
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
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

def reclone_repo(repo_name: str) -> Dict:
    """Reclone a repository (delete and clone again)"""
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
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
