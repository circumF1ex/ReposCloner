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
pip install GitPython
```

Or use the provided batch file:
```bash
start.bat
```

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

## File Structure

```
ReposCloner/
├── main.py              # Main application
├── commit_viewer.py     # Commit viewing utility
├── config.json          # Configuration file (optional)
├── repos.txt            # List of repositories
├── reposcloner.log      # Log file
├── start.bat            # Windows launcher
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

- Python 3.6+
- GitPython library
- Git installed on your system

## License

This project is for educational purposes.

## Contributing

Feel free to submit issues or pull requests for improvements!
