# ReposCloner - Student Conspects Repository Manager

A powerful Python tool for cloning, updating, and managing multiple GitHub repositories containing student conspects (notes).

## Features

### Core Functionality
- ✅ Clone multiple repositories from GitHub
- ✅ Update all repositories with latest changes
- ✅ View commit history and summaries
- ✅ Reclone repositories when needed
- ✅ Export commit summaries to JSON

### Advanced Features
- 🚀 **Parallel Processing**: Process multiple repositories simultaneously for faster operations
- 📊 **Progress Indicators**: Visual progress bars with real-time status updates
- 📈 **Summary Statistics**: Detailed statistics after batch operations
- 🔄 **Retry Logic**: Automatic retries for failed operations
- 🔍 **Search**: Search commit messages across all repositories
- 📝 **Logging**: Comprehensive logging system for debugging
- ⚙️ **Configuration**: Customizable settings via config.json

## Installation

1. Install dependencies:
```bash
py -m pip install -r requirements.txt
```

Or use the provided batch file:
```bash
start.bat
```

> **Windows note:** use the `py` launcher (`py main.py`, `py -m pip ...`).
> A bare `python` command often resolves to the Microsoft Store stub,
> which installs nothing and starts nothing. `start.bat` already uses `py`.

### Web console (optional)

The teacher's web console needs **Python 3.8+** (it requires
`streamlit>=1.30.0`, which has no builds for older Python):

```bash
py -m pip install -r requirements-web.txt
py -m streamlit run web.py
```

Or double-click `start-web.bat` — it refuses to launch on Python < 3.8
and tells you where to get a newer Python instead of failing mid-install.

## Configuration

Create a `config.json` file (or use the default settings):

```json
{
  "repos_dir": "./repos",
  "repos_file": "repos.txt",
  "max_retries": 3,
  "retry_delay": 2,
  "max_workers": 4,
  "enable_logging": true,
  "log_file": "reposcloner.log",
  "log_level": "INFO",
  "auto_parallel": true,
  "default_commit_limit": 50
}
```

## Usage

### Basic Usage

1. Add repository names to `repos.txt` (one per line):
```
username/repo-name
another-user/another-repo
```

2. Run the program:
```bash
python main.py
```

3. Choose from the menu:
   - **Option 1**: Clone all repositories
   - **Option 2**: Update all repositories
   - **Option 3**: Show last commit summaries
   - **Option 4**: View commit history for a repository
   - **Option 5**: Reclone a specific repository
   - **Option 6**: Export commit summaries
   - **Option 7**: Show repository statistics
   - **Option 8**: Search in commit messages
   - **Option 9**: Exit

### Parallel Processing

When cloning or updating, you'll be asked if you want to use parallel processing. This significantly speeds up operations when working with many repositories.

### Searching Commits

Use option 8 to search for text in commit messages across all repositories. Useful for finding specific topics or changes.

## Web Console

`web.py` (via `start-web.bat`, opens http://localhost:8501) offers the same
workflows through a browser: repository inventory with a working scope,
parallel clone/update with progress, a conflict force-update flow, commit
viewer, commit-message search, statistics, and an exportable standalone HTML
dashboard (`reposcloner/report.py`). Both English and Russian are supported
with a sidebar switcher persisted to `config.json`.

Tracked repositories live in `repos.json` (auto-created, git-ignored):
`repos.txt` is only read once to migrate into it, and the app also discovers
checkouts already present in `repos/`. New clones use `owner__repo` directory
names; legacy `owner_repo` checkouts are still recognised.

## File Structure

```
ReposCloner/
├── main.py              # Console application (menu)
├── web.py               # Web console (Streamlit)
├── commit_viewer.py     # Standalone commit viewing utility
├── reposcloner/         # Main package (config, git_operations, repo_store,
│                         #   search, report, i18n, utils)
├── tests/               # pytest suite (offline, git is mocked)
├── config.example.json  # Example configuration (copy to config.json)
├── repos.txt            # Legacy list, read once for migration only
├── repos.json           # Tracked list (auto-created, git-ignored)
├── requirements.txt     # Console dependencies (GitPython)
├── requirements-web.txt # Web console dependencies (Streamlit)
├── requirements-dev.txt # Test dependencies (pytest)
├── start.bat            # Windows console launcher
├── start-web.bat        # Windows web-console launcher
└── repos/               # Cloned repositories directory
```

## Logging

Logs are written to `reposcloner.log` (configurable). Log levels:
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about operations
- **WARNING**: Warning messages
- **ERROR**: Error messages

## Examples

### Clone all repositories in parallel
```
1. Choose option 1
2. Enter 'y' for parallel processing
3. Watch the progress bar
```

### Search for specific topic
```
1. Choose option 8
2. Enter search query (e.g., "homework", "lecture")
3. View matching commits across all repositories
```

## Troubleshooting

### Nothing happens when launching / Store opens
`python` is likely the Microsoft Store stub. Use `py` instead:
`py main.py`, `py -m pip install -r requirements.txt`.
`start.bat` / `start-web.bat` already do this.

### `No matching distribution found for streamlit>=1.30.0`
Your Python is older than 3.8. Either upgrade Python (3.11+ recommended,
https://www.python.org/downloads/) for the web console, or use the console
app (`start.bat`), which works on Python 3.7+.

### Access Denied Errors
If you get access denied errors when recloning:
- Close any file explorers or Git GUIs accessing the repository
- Check if antivirus is blocking file operations
- Manually delete the repository folder and try again

### Network Errors
The tool automatically retries failed operations. If issues persist:
- Check your internet connection
- Verify repository URLs are correct
- Check GitHub status

### Log File
Check `reposcloner.log` for detailed error information and debugging.

## Requirements

- Console app: Python 3.7+
- Web console: Python 3.8+ (Streamlit requirement)
- GitPython library (`requirements.txt`)
- Git installed on your system (GitPython shells out to `git.exe`)

## License

This project is for educational purposes.

## Contributing

Feel free to submit issues or pull requests for improvements!
