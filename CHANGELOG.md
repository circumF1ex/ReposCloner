# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `reposcloner/repo_store.py`: local discovery (scan `repos/` for checkouts) plus
  tracked `repos.json` with per-repo `group` / `enabled` metadata.
- One-time migration: existing `repos.txt` is imported into `repos.json` automatically.
- `pytest` test suite (`tests/`) with mocked git operations — fully offline.
- `requirements.txt`, `requirements-dev.txt`, `config.example.json`.
- Timestamped result files (`changes_results_YYYYMMDD_HHMMSS.json`) instead of overwriting.

### Changed
- `main.py` is now import-safe: configuration loads inside `main()`, so the
  `reposcloner` package can be reused by the future GUI as a plain library.
- `update_repo()` no longer performs a silent `reset --hard` on pull conflicts.
  It reports `status: 'conflict'` and keeps local changes; the CLI asks for
  explicit confirmation before force-updating. New signature:
  `update_repo(repo, repos_dir=None, force=False)`.
- `clone_repo()`, `get_last_commit_summary()`, `view_commit_history()`,
  `reclone_repo()` and `search_in_repos()` accept an optional `repos_dir`.
- Filter (menu option 8) no longer permanently loses the full list: empty input
  or the reset choice restores the full scope; the menu header shows `x/y in scope`.
- Reclone (menu option 5) asks for confirmation before deleting the local copy.
- `print_summary()` reports conflicts as a separate category.

### Fixed
- Rejected unsafe repository ids (`..`, absolute paths, backslashes) that could
  escape `repos_dir` (path traversal via `repos.txt`).
- New clones use `owner__repo` directory names to avoid collisions of the legacy
  `owner_repo` scheme; legacy names are still recognised on read.

### Removed
- `repos.txt` is no longer required. It is only read once for migration when
  no `repos.json` exists.

## [1.0.0] - 2025-11-24

Initial release: parallel clone/update, commit summaries and history viewer,
export to JSON, repository statistics, regex filtering, commit-message search,
retry logic, file logging, `config.json` support.
