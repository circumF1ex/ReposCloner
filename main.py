"""Main entry point for ReposCloner.

Import-safe: importing this module has no side effects. All configuration
loading happens inside :func:`main`, so the future GUI can reuse
:mod:`reposcloner` as a plain library.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from reposcloner.config import is_debug_enabled, load_config, setup_logging
from reposcloner.git_operations import (
    init_git_operations, clone_repo, update_repo, reclone_repo,
    get_last_commit_summary, view_commit_history
)
from reposcloner.i18n import get_lang, t
from reposcloner.utils import print_summary, print_progress
from reposcloner.search import init_search, search_in_repos
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
    lang = get_lang(config)
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
                print(t('migrated', lang, n=len(migrated), src=legacy_file, dst=tracked_path))
                if logger:
                    logger.info(f"Migrated {len(migrated)} repos from {legacy_file}")
        except OSError as e:
            print(f"Warning: could not migrate {legacy_file}: {e}")

    discovered = discover_local_repos(repos_dir)
    items = resolve_work_list(repos_dir, tracked, discovered)
    return items, [i.repo_id for i in items], tracked_path, tracked


def show_menu(active_count: int, total_count: int, lang: str):
    """Display the main menu"""
    scope = f"{active_count}/{total_count}" if active_count != total_count else f"{total_count}"
    print("\n" + "="*60)
    print(f"{t('m_title', lang)}  ({scope})")
    print("="*60)
    for key in ('m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9'):
        print(t(key, lang))
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


def handle_conflicts(results: List[Dict], config: Dict, lang: str) -> List[Dict]:
    """Offer force-update for repos that reported a conflict. Returns updated results."""
    conflicts = [r for r in results if r.get('status') == 'conflict']
    if not conflicts:
        return results
    print(f"\n{t('conflict_list', lang)} ({len(conflicts)}):")
    for r in conflicts:
        print(f"  - {r['repo']}")
    answer = input(t('force_q', lang)).strip().lower()
    if answer != 'y':
        print(t('force_skip', lang))
        return results
    forced = []
    for r in conflicts:
        forced.append(update_repo(r['repo'], repos_dir=_work_repos_dir(config), force=True))
    by_repo = {r['repo']: r for r in forced}
    return [by_repo.get(r['repo'], r) for r in results]


def _parallel_choice(config: Dict, lang: str) -> bool:
    default = 'y' if config['auto_parallel'] else 'n'
    answer = input(t('parallel_q', lang, d=default)).strip().lower()
    if not answer:
        return config['auto_parallel']
    return answer != 'n'


def main(config: Optional[Dict] = None):
    """Main application loop"""
    runtime = build_runtime(config)
    config = runtime['config']
    logger = runtime['logger']
    lang = get_lang(config)
    if '--debug' in sys.argv:
        config['debug'] = True
    debug = is_debug_enabled(config)
    if debug:
        print(t('debug_on', lang))
    logger.info("Starting ReposCloner application")

    repos_dir = _work_repos_dir(config)
    all_items, active_ids, tracked_path, tracked = load_inventory(config, logger)
    all_ids = [i.repo_id for i in all_items]
    repos = list(active_ids)

    if not all_ids:
        print(t('empty_inv', lang))
        logger.warning("Empty inventory: nothing discovered or tracked")

    while True:
        show_menu(len(repos), len(all_ids), lang)
        choice = input(t('choose_opt', lang)).strip()

        if choice == '1':
            parallel = _parallel_choice(config, lang)
            depth = None
            if debug and input(t('shallow_q', lang)).strip().lower() == 'y':
                depth = 1
            clone_fn = (lambda repo: clone_repo(repo, depth=depth)) if depth else clone_repo
            print(f"\n{t('cloning_n', lang, n=len(repos))}")
            if parallel:
                results = process_repos_parallel(repos, clone_fn, 'clone', config)
            else:
                results = process_repos_sequential(repos, clone_fn, 'clone', config)

            print()  # New line after progress
            print_summary(results, "clone", lang)
            if debug:
                print(t('debug_raw', lang))
                print(json.dumps(results, indent=2, ensure_ascii=False))
            filename = save_results(results)
            print(t('results_saved', lang, f=filename))

        elif choice == '2':
            parallel = _parallel_choice(config, lang)
            print(f"\n{t('updating_n', lang, n=len(repos))}")
            if parallel:
                results = process_repos_parallel(repos, update_repo, 'update', config)
            else:
                results = process_repos_sequential(repos, update_repo, 'update', config)
            results = handle_conflicts(results, config, lang)

            print()  # New line after progress
            print_summary(results, "update", lang)
            if debug:
                print(t('debug_raw', lang))
                print(json.dumps(results, indent=2, ensure_ascii=False))
            filename = save_results(results)
            print(t('results_saved', lang, f=filename))

        elif choice == '3':
            print(f"\n{t('fetching_n', lang, n=len(repos))}")
            summaries = []
            for i, repo in enumerate(repos, 1):
                print_progress(i, len(repos), repo, "fetching...")
                summary = get_last_commit_summary(repo)
                summaries.append(summary)
            print()  # New line after progress
            print(f"\n{t('last_title', lang)}")
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
                    print(f"\n{summary['repo']}: {t('not_cloned_l', lang)}")
                elif summary.get('status') in ('error', 'conflict'):
                    print(f"\n{summary['repo']}: {summary.get('status')} - {summary.get('message', 'Unknown')}")
            print("-" * 80)

        elif choice == '4':
            if not repos:
                print(t('no_repos', lang))
                continue
            print(f"\n{t('avail_repos', lang)}")
            for i, repo in enumerate(repos, 1):
                item = next((x for x in all_items if x.repo_id == repo), None)
                status = "✓" if (item and item.cloned) else "✗"
                print(f"{i:2d}. [{status}] {repo}")
            try:
                idx = int(input(f"\n{t('sel_num', lang)}")) - 1
                if 0 <= idx < len(repos):
                    limit_input = input(t('limit_q', lang, d=config['default_commit_limit'])).strip()
                    limit = int(limit_input) if limit_input.isdigit() else config['default_commit_limit']
                    view_commit_history(repos[idx], limit)
                else:
                    print(t('invalid_num', lang))
            except ValueError:
                print(t('invalid_input', lang))

        elif choice == '5':
            if not repos:
                print(t('no_repos', lang))
                continue
            print(t('avail_repos', lang))
            for i, repo in enumerate(repos, 1):
                print(f"{i}. {repo}")
            try:
                idx = int(input(t('sel_reclone', lang))) - 1
                if 0 <= idx < len(repos):
                    confirm = input(t('reclone_confirm', lang, r=repos[idx])).strip().lower()
                    if confirm != 'y':
                        print(t('cancelled', lang))
                        continue
                    result = reclone_repo(repos[idx])
                    print(json.dumps(result, indent=2))
                else:
                    print(t('invalid_num', lang))
            except ValueError:
                print(t('invalid_input', lang))

        elif choice == '6':
            print(f"\n{t('exporting_n', lang, n=len(repos))}")
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
            print(f"\n{t('export_done', lang, f=filename)}")

        elif choice == '7':
            print(f"\n{t('stats_title', lang)}")
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

            print(t('s_total', lang, n=len(repos)) + f" ({len(all_ids)})")
            print(t('s_cloned', lang, n=cloned_count))
            print(t('s_not', lang, n=len(repos) - cloned_count))
            print(t('s_size', lang, mb=total_size / (1024*1024)))
            print(t('s_commits', lang, n=total_commits))
            if cloned_count > 0:
                print(t('s_avg', lang, n=total_commits / cloned_count))
            print("-" * 80)

        elif choice == '8':
            query = input(f"\n{t('search_q', lang)}").strip()
            if query:
                print(f"\n{t('searching_q', lang, q=query)}")
                results = search_in_repos(query, repos)
                if results:
                    print(f"\n{t('found_repos', lang, n=len(results))}")
                    print("=" * 80)
                    total_matches = 0
                    for result in results:
                        total_matches += result['count']
                        print(f"\n{result['repo']} ({result['count']}):")
                        print("-" * 80)
                        for match in result['matches'][:10]:  # Show first 10 matches per repo
                            date = datetime.fromisoformat(match['date']).strftime('%Y-%m-%d %H:%M')
                            print(f"  {match['hash']} | {date} | {match['author']:20s} | {match['message']}")
                        if result['count'] > 10:
                            print(t('more_matches', lang, k=result['count'] - 10))
                    print("=" * 80)
                    print(t('total_matches', lang, t=total_matches, r=len(results)))
                else:
                    print(t('no_match', lang, q=query))
            else:
                print(t('no_query', lang))

        elif choice == '9':
            print(f"\n{t('goodbye', lang)}")
            logger.info("Application exited by user")
            break

        else:
            print(t('invalid_choice', lang))


if __name__ == '__main__':
    main()
