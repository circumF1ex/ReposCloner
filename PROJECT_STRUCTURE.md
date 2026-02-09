# Project Structure

## Overview
This document describes the improved project structure of ReposCloner.

## Directory Structure

```
ReposCloner/
├── reposcloner/          # Main package
│   ├── __init__.py      # Package initialization and exports
│   ├── config.py        # Configuration management
│   ├── git_operations.py # Git operations (clone, update, etc.)
│   ├── utils.py         # Utility functions (progress, summaries)
│   └── search.py        # Search and filtering functionality
│
├── tests/               # Test files
│   └── test_main.py     # Unit tests
│
├── main.py              # Main entry point
├── commit_viewer.py     # Commit viewing utility (standalone)
├── config.json          # Configuration file
├── repos.txt            # List of repositories
│
├── start.bat            # Windows launcher script
├── run_commit_viewer.bat # Commit viewer launcher
│
├── README.md            # Main documentation
├── IMPROVEMENTS.md      # List of improvements
├── PROJECT_STRUCTURE.md # This file
│
└── repos/               # Cloned repositories (generated)
```

## Module Descriptions

### `reposcloner/` Package

#### `__init__.py`
- Package initialization
- Exports main functions and classes
- Version information

#### `config.py`
- Configuration loading from `config.json`
- Default configuration values
- Logging setup
- Functions:
  - `load_config()` - Load configuration
  - `setup_logging()` - Initialize logging

#### `git_operations.py`
- All Git-related operations
- Functions:
  - `init_git_operations()` - Initialize module with config
  - `clone_repo()` - Clone a repository
  - `update_repo()` - Update a repository
  - `reclone_repo()` - Reclone a repository
  - `get_last_commit_summary()` - Get last commit info
  - `view_commit_history()` - Display commit history

#### `utils.py`
- Utility functions for UI and data processing
- Functions:
  - `load_repos()` - Load repository list from file
  - `print_summary()` - Print operation summary
  - `print_progress()` - Display progress bar

#### `search.py`
- Search and filtering functionality
- Functions:
  - `init_search()` - Initialize module with config
  - `filter_repos()` - Filter repositories by pattern
  - `search_in_repos()` - Search commit messages

### Root Files

#### `main.py`
- Main application entry point
- Menu system
- Orchestrates all operations
- Uses modules from `reposcloner/` package

#### `commit_viewer.py`
- Standalone commit viewing utility
- Can be run independently
- Uses subprocess for git commands

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
from reposcloner.utils import load_repos, print_progress
from reposcloner.search import filter_repos, search_in_repos

# Or import everything from __init__
from reposcloner import clone_repo, update_repo, load_repos
```

## Adding New Features

1. **New Git Operation**: Add to `reposcloner/git_operations.py`
2. **New Utility Function**: Add to `reposcloner/utils.py`
3. **New Search Feature**: Add to `reposcloner/search.py`
4. **New Configuration Option**: Update `reposcloner/config.py` and `config.json`
5. **New Menu Option**: Add to `main.py` menu and handler

## Testing

Tests are located in the `tests/` directory. Run tests with:

```bash
python -m unittest tests.test_main
```

## Configuration

Configuration is managed through `config.json`. Default values are defined in `reposcloner/config.py`.
