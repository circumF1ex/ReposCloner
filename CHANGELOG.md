# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `AGENTS.md`: developer notes for future sessions (architecture, standing
  decisions, gotchas).

### Fixed
- CLI conflict prompt no longer prints a stray bare-number line before the
  conflict list.
- Switching web console language no longer leaves stale translated widget
  values (`danger_*`) that mismatch the rebuilt options.

## [1.2.0] - 2026-09-07

### Added
- Local web console for teachers (`web.py`, Streamlit): repository inventory
  with working scope, parallel clone/update with progress, conflict
  force-update flow, commit viewer, commit-message search, statistics.
- `reposcloner/report.py`: standalone HTML dashboard builder + download from
  the web console (no server needed to view the exported file).
- `get_commit_history()` data API in `git_operations` (the print-only
  `view_commit_history` remains for the CLI).
- `delete_repo_checkout()` in `git_operations` + "Danger zone" in the web
  console: remove a repo from the tracked list, optionally deleting its
  local files (with confirmation checkbox).
- Operations in the web console now refresh the inventory table immediately
  and report results via persistent notices.
- `requirements-web.txt`, `start-web.bat` launcher.
- `repos.json` (the private wanted-list) is git-ignored: inventory comes from
  filesystem discovery plus one-by-one adding in the UI, never from commits.
- EN/RU localization (`reposcloner/i18n.py`, Russian primary and default):
  full web console in both languages with a sidebar switcher persisted to
  `config.json`, CLI menu and summaries in both languages.
- "Debug info" panel in the web console: environment paths plus raw
  per-repo JSON of the last clone/update.

### Changed
- Pattern-based repository filtering removed from the CLI menu and the web
  console (the working-scope multiselect covers narrowing down the set).
- Debug tooling is hidden behind a switch instead of a separate branch:
  `REPOSCLONER_DEBUG=1`, CLI `--debug`, or web `?debug=1` enables the
  shallow-clone option, raw-result dumps (CLI) and the Debug info panel
  (web). Off by default; `clone_repo(..., depth=1)` stays in the core.

### Fixed
- Web Update notice no longer shows silent "0 of everything" when repos are
  not cloned yet — it now says how many are missing and points at Clone.

## [1.1.0] - 2026-09-07

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
