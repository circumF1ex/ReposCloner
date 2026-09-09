# Project Structure

## Overview
This document describes the project structure of ReposCloner.

## Directory Structure

```
ReposCloner/
├── reposcloner/          # Main package
│   ├── __init__.py      # Package initialization and exports
│   ├── config.py        # Configuration management
│   ├── git_operations.py # Git operations (clone, update, reclone, history)
│   ├── repo_store.py    # Inventory: discovery + tracked repos.json
│   ├── search.py        # Search and filtering functionality
│   ├── report.py        # Standalone HTML dashboard builder
│   ├── i18n.py          # EN/RU localization (Russian default)
│   └── utils.py         # Utility functions (progress, summaries)
│
├── tests/               # pytest suite (offline, git is mocked)
│   ├── test_config.py
│   ├── test_git_operations.py
│   ├── test_i18n.py
│   ├── test_repo_store.py
│   ├── test_report.py
│   └── test_search.py
│
├── main.py              # Console entry point (menu, import-safe)
├── web.py               # Web console (Streamlit)
├── commit_viewer.py     # Standalone commit viewer (subprocess-based)
├── config.example.json  # Example configuration (copy to config.json)
├── repos.txt            # Legacy list, read once for migration only
├── repos.json           # Tracked list (auto-created, git-ignored)
│
├── requirements.txt     # Console dependencies (GitPython)
├── requirements-web.txt # Web console dependencies (Streamlit)
├── requirements-dev.txt # Test dependencies (pytest)
├── start.bat            # Windows console launcher (uses `py`)
├── start-web.bat        # Windows web-console launcher (uses `py`)
│
├── README.md            # Main documentation
├── CHANGELOG.md         # Release history (Keep a Changelog)
├── IMPROVEMENTS.md      # Feature/improvement notes
├── PROJECT_STRUCTURE.md # This file
│
└── repos/               # Cloned repositories (generated, git-ignored)
```

Generated/git-ignored files (`config.json`, `repos.json`, `repos/`,
`*.log`, `changes_results_*.json`, `commit_summaries_*.json`) are not
committed — see `.gitignore`.

## Module Descriptions

### `reposcloner/` Package

#### `__init__.py`
- Package initialization
- Exports main functions and classes
- Version information

#### `config.py`
- Configuration loading from `config.json` (with built-in defaults)
- Hidden debug switch (`REPOSCLONER_DEBUG=1` / `debug: true` / `--debug`)
- Logging setup
- Functions:
  - `load_config()` - Load configuration
  - `save_config()` - Persist configuration (e.g. web language choice)
  - `is_debug_enabled()` - Resolve the debug switch
  - `setup_logging()` - Initialize logging

#### `git_operations.py`
- All Git-related operations (each accepts an optional `repos_dir`)
- Functions:
  - `init_git_operations()` - Initialize module defaults (legacy CLI path)
  - `clone_repo()` - Clone a repository (retry logic, optional `depth`)
  - `update_repo()` - Pull; reports `conflict` unless `force=True`
  - `reclone_repo()` - Delete and clone again (access-denied hints)
  - `delete_repo_checkout()` - Delete a local checkout directory
  - `get_last_commit_summary()` - Last commit info (data)
  - `get_commit_history()` - Commit history (data, for web/API)
  - `view_commit_history()` - Print commit history (CLI)

#### `repo_store.py`
- Inventory: filesystem discovery (dirs containing `.git`) merged with the
  tracked `repos.json` wanted-list (per-repo `group` / `enabled`)
- `owner__repo` directory names for new clones; legacy `owner_repo`
  names recognised on read
- Strict `owner/repo` validation (rejects path traversal)
- One-time `repos.txt` migration via `import_repos_txt()`

#### `search.py`
- Search and filtering functionality
- Functions:
  - `init_search()` - Initialize module with config (legacy CLI path)
  - `filter_repos()` - Filter repository ids by regex (library helper;
    no longer a CLI menu item since 1.2.0)
  - `search_in_repos()` - Search commit messages (recent commits per repo)

#### `report.py`
- `build_dashboard_html()` - pure function returning a self-contained HTML
  status page (used by the web "Export HTML" button, unit-tested)

#### `i18n.py`
- EN/RU strings, Russian primary and default
- `get_lang(config)`, `t(key, lang, **kwargs)` with ru-fallback

#### `utils.py`
- Utility functions for UI and data processing
- Functions:
  - `load_repos()` - Load repository list from a text file (legacy helper)
  - `print_summary()` - Print operation summary (incl. conflicts)
  - `print_progress()` - Display progress bar

### Root Files

#### `main.py`
- Console application entry point (options 1–9: clone, update, summaries,
  history, reclone, export, statistics, search, exit)
- Import-safe: config loads inside `main()`, reusable as a library

#### `web.py`
- Streamlit teacher console: inventory + working scope, parallel
  clone/update, conflict force-update, commit viewer, search, statistics,
  HTML dashboard export, danger-zone removal, debug panel

#### `commit_viewer.py`
- Standalone commit viewing utility (uses `git` subprocess directly)
- Can be run independently; supports author filter

## Benefits of This Structure

1. **Modularity**: Code is organized into logical modules
2. **Maintainability**: Easy to find and modify specific functionality
3. **Testability**: Each module can be tested independently
4. **Reusability**: Modules can be imported and used elsewhere
5. **Scalability**: Easy to add new features without cluttering main.py
6. **Separation of Concerns**: Each module has a single responsibility

## Import Examples

```python
# Import from package
from reposcloner.config import load_config, setup_logging
from reposcloner.git_operations import clone_repo, update_repo
from reposcloner.utils import print_summary, print_progress
from reposcloner.search import search_in_repos
from reposcloner.repo_store import resolve_work_list, validate_repo_id

# Or import everything from __init__
from reposcloner import clone_repo, update_repo
```

## Adding New Features

1. **New Git Operation**: Add to `reposcloner/git_operations.py`
2. **New Utility Function**: Add to `reposcloner/utils.py`
3. **New Search Feature**: Add to `reposcloner/search.py`
4. **New Configuration Option**: Update `reposcloner/config.py` and `config.example.json`
5. **New Menu Option**: Add to `main.py` menu and handler (+ `i18n.py` strings)
6. **New Web Tab**: Add to `web.py` (+ `i18n.py` strings)

## Testing

Tests are located in the `tests/` directory. They are fully offline
(git operations are mocked). Run them with:

```bash
py -m pytest tests/ -q
```

## Configuration

Configuration is managed through `config.json` (create it by copying
`config.example.json`). Default values are defined in `reposcloner/config.py`.
