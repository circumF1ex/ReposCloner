"""Main entry point for ReposCloner.

Import-safe: importing this module has no side effects. All configuration
loading happens inside :func:`main`, so the future GUI can reuse
:mod:`reposcloner` as a plain library.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from reposcloner.config import load_config, setup_logging
from reposcloner.git_operations import (
    init_git_operations, clone_repo, update_repo, reclone_repo,
    get_last_commit_summary, view_commit_history
)
from reposcloner.utils import print_summary, print_progress
from reposcloner.search import init_search, filter_repos, search_in_repos
from reposcloner.repo_store import (
    TrackedRepo, WorkItem, load_tracked, save_tracked,
    import_repos_txt, discover_local_repos, resolve_work_list,
)

TRACKED_FILENAME = 'repos.json'


def build_runtime(config: Optional[Dict] = None) -> Dict:
    """Load config, set up logging and legacy module defaults."""
    config = config or load_config()
    logger = setup_logging(config)
    init_git_operations(config['repos_dir'], config['max_retries'], config['retry_delay'])
    init_search(config['repos_dir'])
    return {'config': config, 'logger': logger}


def tracked_candidates(config: Dict) -> List[str]:
    """Possible locations for repos.json (project root first, then repos dir)."""
    return [
        os.path.abspath(TRACKED_FILENAME),
        os.path.abspath(os.path.join(config['repos_dir'], TRACKED_FILENAME)),
    ]


def load_inventory(config: Dict, logger=None):
    """Build the merged work list: discovery + tracked + legacy import.

    Returns (all_items, active_ids, tracked_path, tracked_entries).
    """
    repos_dir = config['repos_dir']
    os.makedirs(repos_dir, exist_ok=True)

    tracked_path = None
    tracked: List[TrackedRepo] = []
    for candidate in tracked_candidates(config):
        if os.path.exists(candidate):
            tracked_path = candidate
            try:
                tracked = load_tracked(candidate)
            except ValueError as e:
                print(f"Warning: {e}")
                tracked = []
            break
    if tracked_path is None:
        tracked_path = tracked_candidates(config)[0]

    # One-time legacy migration: repos.txt -> repos.json (only if no tracked file).
    legacy_file = config.get('repos_file', 'repos.txt')
    if not tracked and os.path.exists(legacy_file):
        try:
            migrated = import_repos_txt(legacy_file)
            if migrated:
                tracked = migrated
                save_tracked(tracked_path, tracked)
                print(f"Migrated {len(migrated)} repositories from {legacy_file} "
                      f"to {tracked_path}. You can now delete {legacy_file}.")
                if logger:
                    logger.info(f"Migrated {len(migrated)} repos from {legacy_file}")
        except OSError as e:
            print(f"Warning: could not migrate {legacy_file}: {e}")

    discovered = discover_local_repos(repos_dir)
    items = resolve_work_list(repos_dir, tracked, discovered)
    return items, [i.repo_id for i in items], tracked_path, tracked


def show_menu(active_count: int, total_count: int):
    """Display the main menu"""
    scope = f"{active_count}/{total_count} repos in scope" if active_count != total_count else f"{total_count} repositories"
    print("\n" + "="*60)
    print(f"REPOSITORY CLONER & UPDATER  ({scope})")
    print("="*60)
    print("1. Clone all repositories (only if not cloned)")
    print("2. Update all repositories")
    print("3. Show last commit summary for all repositories")
    print("4. View commit history for a selected repository")
    print("5. Reclone a specific repository")
    print("6. Export commit summaries to JSON")
    print("7. Show repository statistics")
    print("8. Filter repositories by name pattern (empty input resets)")
    print("9. Search in commit messages across repositories")
    print("10. Exit")
    print("="*60)


def _work_repos_dir(config: Dict) -> str:
    return config['repos_dir']


def process_repos_parallel(repos: List[str], operation_func, operation_name: str, config: Dict):
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

    with ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
        future_to_repo = {executor.submit(process_with_progress, repo): repo for repo in repos}
        for future in as_completed(future_to_repo):
            results.append(future.result())

    return results


def process_repos_sequential(repos: List[str], operation_func, operation_name: str, config: Dict):
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


def save_results(results: List[Dict], prefix: str = 'changes_results') -> str:
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    return filename


def handle_conflicts(results: List[Dict], config: Dict) -> List[Dict]:
    """Offer force-update for repos that reported a conflict. Returns updated results."""
    conflicts = [r for r in results if r.get('status') == 'conflict']
    if not conflicts:
        return results
    print(f"\n{len(conflicts)} repositorie(s) have local changes blocking the update:")
    for r in conflicts:
        print(f"  - {r['repo']}")
    answer = input("Discard local changes and force-update them? (y/N): ").strip().lower()
    if answer != 'y':
        print("Kept local changes. Re-run with force after reviewing.")
        return results
    forced = []
    for r in conflicts:
        forced.append(update_repo(r['repo'], repos_dir=_work_repos_dir(config), force=True))
    by_repo = {r['repo']: r for r in forced}
    return [by_repo.get(r['repo'], r) for r in results]


def main(config: Optional[Dict] = None):
    """Main application loop"""
    runtime = build_runtime(config)
    config = runtime['config']
    logger = runtime['logger']
    logger.info("Starting ReposCloner application")

    repos_dir = _work_repos_dir(config)
    all_items, active_ids, tracked_path, tracked = load_inventory(config, logger)
    all_ids = [i.repo_id for i in all_items]
    repos = list(active_ids)

    if not all_ids and not os.listdir(repos_dir):
        print("No repositories found. Clone one via option 1 after adding it to "
              f"{tracked_path}, or place checkouts in {repos_dir}.")
        logger.warning("Empty inventory: nothing discovered or tracked")
    elif not all_ids:
        print(f"Discovered {len(discover_local_repos(repos_dir))} local checkouts.")

    while True:
        show_menu(len(repos), len(all_ids))
        choice = input("Choose an option: ").strip()

        if choice == '1':
            use_parallel = input(f"Use parallel processing? (y/n, default={'y' if config['auto_parallel'] else 'n'}): ").strip().lower()
            if not use_parallel:
                parallel = config['auto_parallel']
            else:
                parallel = use_parallel != 'n'

            print(f"\nCloning {len(repos)} repositories...")
            if parallel:
                results = process_repos_parallel(repos, clone_repo, 'clone', config)
            else:
                results = process_repos_sequential(repos, clone_repo, 'clone', config)

            print()  # New line after progress
            print_summary(results, "clone")
            filename = save_results(results)
            print(f"Results saved to {filename}")

        elif choice == '2':
            use_parallel = input(f"Use parallel processing? (y/n, default={'y' if config['auto_parallel'] else 'n'}): ").strip().lower()
            if not use_parallel:
                parallel = config['auto_parallel']
            else:
                parallel = use_parallel != 'n'

            print(f"\nUpdating {len(repos)} repositories...")
            if parallel:
                results = process_repos_parallel(repos, update_repo, 'update', config)
            else:
                results = process_repos_sequential(repos, update_repo, 'update', config)
            results = handle_conflicts(results, config)

            print()  # New line after progress
            print_summary(results, "update")
            filename = save_results(results)
            print(f"Results saved to {filename}")

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
                elif summary.get('status') in ('error', 'conflict'):
                    print(f"\n{summary['repo']}: {summary.get('status')} - {summary.get('message', 'Unknown')}")
            print("-" * 80)

        elif choice == '4':
            if not repos:
                print("No repositories available.")
                continue
            print("\nAvailable repositories:")
            for i, repo in enumerate(repos, 1):
                item = next((x for x in all_items if x.repo_id == repo), None)
                status = "✓" if (item and item.cloned) else "✗"
                print(f"{i:2d}. [{status}] {repo}")
            try:
                idx = int(input("\nSelect repository number: ")) - 1
                if 0 <= idx < len(repos):
                    limit_input = input(f"Limit number of commits (press Enter for {config['default_commit_limit']}): ").strip()
                    limit = int(limit_input) if limit_input.isdigit() else config['default_commit_limit']
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
                    confirm = input(f"Delete local copy of {repos[idx]} and clone again? (y/N): ").strip().lower()
                    if confirm != 'y':
                        print("Cancelled.")
                        continue
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
                item = next((x for x in all_items if x.repo_id == repo_name), None)
                repo_path = item.path if item else os.path.join(repos_dir, repo_name.replace('/', '_'))
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

            print(f"Total repositories in scope: {len(repos)} (tracked total: {len(all_ids)})")
            print(f"Cloned repositories: {cloned_count}")
            print(f"Not cloned: {len(repos) - cloned_count}")
            print(f"Total size: {total_size / (1024*1024):.2f} MB")
            print(f"Total commits: {total_commits}")
            if cloned_count > 0:
                print(f"Average commits per repo: {total_commits / cloned_count:.1f}")
            print("-" * 80)

        elif choice == '8':
            pattern = input("\nEnter repository name pattern (regex, case-insensitive; empty resets): ").strip()
            if not pattern:
                repos = list(all_ids)
                print(f"Scope reset to all {len(repos)} repositories.")
                continue
            if pattern:
                filtered = filter_repos(all_ids, pattern)
                if filtered:
                    print(f"\nFound {len(filtered)} repositories matching '{pattern}':")
                    print("-" * 60)
                    for i, repo in enumerate(filtered, 1):
                        item = next((x for x in all_items if x.repo_id == repo), None)
                        status = "✓ Cloned" if (item and item.cloned) else "✗ Not cloned"
                        print(f"{i:2d}. [{status}] {repo}")
                    print("-" * 60)

                    use_filtered = input("\nUse filtered repositories? ([y]es / [n]o / [r]eset): ").strip().lower()
                    if use_filtered == 'y':
                        repos = filtered
                        print(f"Now working with {len(repos)} filtered repositories.")
                    elif use_filtered == 'r':
                        repos = list(all_ids)
                        print(f"Scope reset to all {len(repos)} repositories.")
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
