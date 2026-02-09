"""Main entry point for ReposCloner"""

import os
import json
from datetime import datetime
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from reposcloner.config import load_config, setup_logging
from reposcloner.git_operations import (
    init_git_operations, clone_repo, update_repo, reclone_repo,
    get_last_commit_summary, view_commit_history
)
from reposcloner.utils import load_repos, print_summary, print_progress
from reposcloner.search import init_search, filter_repos, search_in_repos

# Load configuration
config = load_config()
logger = setup_logging(config)

# Initialize modules with configuration
REPOS_DIR = config['repos_dir']
MAX_RETRIES = config['max_retries']
RETRY_DELAY = config['retry_delay']
MAX_WORKERS = config['max_workers']
DEFAULT_COMMIT_LIMIT = config['default_commit_limit']

init_git_operations(REPOS_DIR, MAX_RETRIES, RETRY_DELAY)
init_search(REPOS_DIR)

def show_menu():
    """Display the main menu"""
    print("\n" + "="*60)
    print("REPOSITORY CLONER & UPDATER")
    print("="*60)
    print("1. Clone all repositories (only if not cloned)")
    print("2. Update all repositories")
    print("3. Show last commit summary for all repositories")
    print("4. View commit history for a selected repository")
    print("5. Reclone a specific repository")
    print("6. Export commit summaries to JSON")
    print("7. Show repository statistics")
    print("8. Filter repositories by name pattern")
    print("9. Search in commit messages across repositories")
    print("10. Exit")
    print("="*60)

def process_repos_parallel(repos: List[str], operation_func, operation_name: str):
    """Process repositories in parallel"""
    completed = 0
    lock = threading.Lock()
    results = []
    
    def process_with_progress(repo):
        nonlocal completed
        result = operation_func(repo)
        with lock:
            completed += 1
            if operation_name == 'clone':
                status_icon = "✓" if result.get('status') in ['cloned', 'already_cloned'] else "✗"
                print_progress(completed, len(repos), repo, f"{status_icon} {result.get('status')}")
            elif operation_name == 'update':
                status_icon = "✓" if result.get('status') in ['updated', 'updated_forced', 'no_changes'] else "✗"
                commits_info = f" ({result.get('new_commits_count', 0)} new)" if result.get('new_commits_count', 0) > 0 else ""
                print_progress(completed, len(repos), repo, f"{status_icon} {result.get('status')}{commits_info}")
        return result
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_repo = {executor.submit(process_with_progress, repo): repo for repo in repos}
        for future in as_completed(future_to_repo):
            results.append(future.result())
    
    return results

def process_repos_sequential(repos: List[str], operation_func, operation_name: str):
    """Process repositories sequentially"""
    results = []
    for i, repo in enumerate(repos, 1):
        if operation_name == 'clone':
            print_progress(i, len(repos), repo, "cloning...")
        elif operation_name == 'update':
            print_progress(i, len(repos), repo, "updating...")
        result = operation_func(repo)
        results.append(result)
        if operation_name == 'clone':
            status_icon = "✓" if result.get('status') in ['cloned', 'already_cloned'] else "✗"
            print_progress(i, len(repos), repo, f"{status_icon} {result.get('status')}")
        elif operation_name == 'update':
            status_icon = "✓" if result.get('status') in ['updated', 'updated_forced', 'no_changes'] else "✗"
            commits_info = f" ({result.get('new_commits_count', 0)} new)" if result.get('new_commits_count', 0) > 0 else ""
            print_progress(i, len(repos), repo, f"{status_icon} {result.get('status')}{commits_info}")
    return results

def main():
    """Main application loop"""
    logger.info("Starting ReposCloner application")
    if not os.path.exists(REPOS_DIR):
        os.makedirs(REPOS_DIR)
        logger.info(f"Created repositories directory: {REPOS_DIR}")
    
    repos = load_repos(config['repos_file'])
    
    if not repos:
        print("No repositories found in repos.txt. Please add repositories and try again.")
        logger.warning("No repositories found in repos.txt")
        return
    
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()
        
        if choice == '1':
            use_parallel = input(f"Use parallel processing? (y/n, default={'y' if config['auto_parallel'] else 'n'}): ").strip().lower()
            if not use_parallel:
                parallel = config['auto_parallel']
            else:
                parallel = use_parallel != 'n'
            
            print(f"\nCloning {len(repos)} repositories...")
            if parallel:
                results = process_repos_parallel(repos, clone_repo, 'clone')
            else:
                results = process_repos_sequential(repos, clone_repo, 'clone')
            
            print()  # New line after progress
            print_summary(results, "clone")
            with open('changes_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print("Results saved to changes_results.json")
        
        elif choice == '2':
            use_parallel = input(f"Use parallel processing? (y/n, default={'y' if config['auto_parallel'] else 'n'}): ").strip().lower()
            if not use_parallel:
                parallel = config['auto_parallel']
            else:
                parallel = use_parallel != 'n'
            
            print(f"\nUpdating {len(repos)} repositories...")
            if parallel:
                results = process_repos_parallel(repos, update_repo, 'update')
            else:
                results = process_repos_sequential(repos, update_repo, 'update')
            
            print()  # New line after progress
            print_summary(results, "update")
            with open('changes_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print("Results saved to changes_results.json")
        
        elif choice == '3':
            print(f"\nFetching last commit summaries for {len(repos)} repositories...")
            summaries = []
            for i, repo in enumerate(repos, 1):
                print_progress(i, len(repos), repo, "fetching...")
                summary = get_last_commit_summary(repo)
                summaries.append(summary)
            print()  # New line after progress
            print("\nLast Commit Summaries:")
            print("-" * 80)
            for summary in summaries:
                if 'last_commit' in summary:
                    commit = summary['last_commit']
                    date = datetime.fromisoformat(commit['date']).strftime('%Y-%m-%d %H:%M')
                    print(f"\n{summary['repo']}:")
                    print(f"  Hash: {commit['hash'][:7]}")
                    print(f"  Date: {date}")
                    print(f"  Author: {commit['author']}")
                    print(f"  Message: {commit['message'][:100]}{'...' if len(commit['message']) > 100 else ''}")
                elif summary.get('status') == 'not_cloned':
                    print(f"\n{summary['repo']}: Not cloned")
                elif summary.get('status') == 'error':
                    print(f"\n{summary['repo']}: Error - {summary.get('message', 'Unknown')}")
            print("-" * 80)
        
        elif choice == '4':
            if not repos:
                print("No repositories available.")
                continue
            print("\nAvailable repositories:")
            for i, repo in enumerate(repos, 1):
                repo_path = os.path.join(REPOS_DIR, repo.replace('/', '_'))
                status = "✓" if os.path.exists(repo_path) else "✗"
                print(f"{i:2d}. [{status}] {repo}")
            try:
                idx = int(input("\nSelect repository number: ")) - 1
                if 0 <= idx < len(repos):
                    limit_input = input(f"Limit number of commits (press Enter for {DEFAULT_COMMIT_LIMIT}): ").strip()
                    limit = int(limit_input) if limit_input.isdigit() else DEFAULT_COMMIT_LIMIT
                    view_commit_history(repos[idx], limit)
                else:
                    print("Invalid number.")
            except ValueError:
                print("Invalid input.")
        
        elif choice == '5':
            if not repos:
                print("No repositories available.")
                continue
            print("Available repositories:")
            for i, repo in enumerate(repos, 1):
                print(f"{i}. {repo}")
            try:
                idx = int(input("Select repository number to reclone: ")) - 1
                if 0 <= idx < len(repos):
                    result = reclone_repo(repos[idx])
                    print(json.dumps(result, indent=2))
                else:
                    print("Invalid number.")
            except ValueError:
                print("Invalid input.")
        
        elif choice == '6':
            print(f"\nExporting commit summaries for {len(repos)} repositories...")
            summaries = []
            for i, repo in enumerate(repos, 1):
                print_progress(i, len(repos), repo, "exporting...")
                summary = get_last_commit_summary(repo)
                summaries.append(summary)
            print()  # New line after progress
            
            filename = f"commit_summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'total_repos': len(repos),
                    'summaries': summaries
                }, f, indent=2, ensure_ascii=False)
            print(f"\nExport completed! Saved to {filename}")
        
        elif choice == '7':
            print("\nRepository Statistics:")
            print("-" * 80)
            cloned_count = 0
            total_size = 0
            total_commits = 0
            
            from git import Repo as GitRepo
            for repo_name in repos:
                repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
                if os.path.exists(repo_path):
                    cloned_count += 1
                    try:
                        repo = GitRepo(repo_path)
                        # Calculate directory size
                        repo_size = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, dirnames, filenames in os.walk(repo_path)
                            for filename in filenames
                        )
                        total_size += repo_size
                        # Count commits
                        commit_count = sum(1 for _ in repo.iter_commits())
                        total_commits += commit_count
                    except Exception:
                        pass
            
            print(f"Total repositories in list: {len(repos)}")
            print(f"Cloned repositories: {cloned_count}")
            print(f"Not cloned: {len(repos) - cloned_count}")
            print(f"Total size: {total_size / (1024*1024):.2f} MB")
            print(f"Total commits: {total_commits}")
            if cloned_count > 0:
                print(f"Average commits per repo: {total_commits / cloned_count:.1f}")
            print("-" * 80)
        
        elif choice == '8':
            pattern = input("\nEnter repository name pattern (regex supported, case-insensitive): ").strip()
            if pattern:
                filtered_repos = filter_repos(repos, pattern)
                if filtered_repos:
                    print(f"\nFound {len(filtered_repos)} repositories matching '{pattern}':")
                    print("-" * 60)
                    for i, repo in enumerate(filtered_repos, 1):
                        repo_path = os.path.join(REPOS_DIR, repo.replace('/', '_'))
                        status = "✓ Cloned" if os.path.exists(repo_path) else "✗ Not cloned"
                        print(f"{i:2d}. [{status}] {repo}")
                    print("-" * 60)
                    
                    use_filtered = input("\nUse filtered repositories for next operation? (y/n): ").strip().lower()
                    if use_filtered == 'y':
                        repos = filtered_repos
                        print(f"Now working with {len(repos)} filtered repositories.")
                else:
                    print(f"No repositories found matching pattern '{pattern}'")
            else:
                print("No pattern provided.")
        
        elif choice == '9':
            query = input("\nEnter search query (searches in commit messages): ").strip()
            if query:
                print(f"\nSearching for '{query}' in commit messages...")
                results = search_in_repos(query, repos)
                if results:
                    print(f"\nFound {len(results)} repositories with matching commits:")
                    print("=" * 80)
                    total_matches = 0
                    for result in results:
                        total_matches += result['count']
                        print(f"\n{result['repo']} ({result['count']} matches):")
                        print("-" * 80)
                        for match in result['matches'][:10]:  # Show first 10 matches per repo
                            date = datetime.fromisoformat(match['date']).strftime('%Y-%m-%d %H:%M')
                            print(f"  {match['hash']} | {date} | {match['author']:20s} | {match['message']}")
                        if result['count'] > 10:
                            print(f"  ... and {result['count'] - 10} more matches")
                    print("=" * 80)
                    print(f"Total: {total_matches} matches across {len(results)} repositories")
                else:
                    print(f"No commits found containing '{query}'")
            else:
                print("No search query provided.")
        
        elif choice == '10':
            print("\nGoodbye!")
            logger.info("Application exited by user")
            break
        
        else:
            print("Invalid choice. Please select a number from 1-10.")

if __name__ == '__main__':
    main()
