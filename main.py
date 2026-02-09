import os
import sys
import shutil
import time
from git import Repo, GitCommandError
import json
from pathlib import Path

# Папка для локального хранения репозиториев
REPOS_DIR = './repos'

def load_repos(repos_file='repos.txt'):
    with open(repos_file, 'r') as f:
        repos = [line.strip() for line in f if line.strip()]
    return repos

def clone_repo(repo_name):
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
    if os.path.exists(repo_path):
        return {'repo': repo_name, 'status': 'already_cloned'}
    try:
        Repo.clone_from(f'https://github.com/{repo_name}.git', repo_path, config=['core.longpaths=true', 'core.quotepath=false'])
        return {'repo': repo_name, 'status': 'cloned'}
    except GitCommandError as e:
        return {'repo': repo_name, 'status': 'error', 'message': str(e)}

def update_repo(repo_name):
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
    if not os.path.exists(repo_path):
        return {'repo': repo_name, 'status': 'not_cloned'}
    try:
        repo = Repo(repo_path)
        old_commit = repo.head.commit.hexsha
        origin = repo.remotes.origin
        origin.pull()
        new_commit = repo.head.commit.hexsha
        if old_commit != new_commit:
            new_commits = list(repo.iter_commits(f'{old_commit}..{new_commit}'))
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
            repo.git.fetch()
            current_branch = repo.active_branch.name
            repo.git.reset('--hard', f'origin/{current_branch}')
            new_commit = repo.head.commit.hexsha
            if old_commit != new_commit:
                new_commits = list(repo.iter_commits(f'{old_commit}..{new_commit}'))
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
    return changes

def get_last_commit_summary(repo_name):
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

def view_commit_history(repo_name):
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
    if not os.path.exists(repo_path):
        print(f"Repository {repo_name} not cloned.")
        return
    try:
        repo = Repo(repo_path)
        commits = list(repo.iter_commits())
        if commits:
            print(f"Commit history for {repo_name}:")
            for commit in commits:
                print(f"{commit.hexsha[:7]} {commit.authored_datetime.isoformat()} {commit.author.name}: {commit.message.strip()}")
        else:
            print(f"No commits in {repo_name}.")
    except Exception as e:
        print(f"Error viewing history: {str(e)}")

def reclone_repo(repo_name):
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
    env = os.environ.copy()
    env['GIT_CONFIG_PARAMETERS'] = 'core.longpaths=true core.quotepath=false'
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
        Repo.clone_from(f'https://github.com/{repo_name}.git', repo_path, env=env)
        return {'repo': repo_name, 'status': 'recloned'}
    except Exception as e:
        if 'WinError 5' in str(e) or 'Access denied' in str(e):
            message = f"Access denied while deleting repository directory. Please ensure no other processes are using the files (e.g., close Git GUI, file explorer, or antivirus). You may need to manually delete the folder '{repo_path}' and try again. Original error: {str(e)}"
        else:
            message = str(e)
        return {'repo': repo_name, 'status': 'error', 'message': message}

def show_menu():
    print("\nMenu:")
    print("1. Clone all repositories (only if not cloned)")
    print("2. Update all repositories")
    print("3. Show last commit summary for all repositories")
    print("4. View commit history for a selected repository")
    print("5. Reclone a specific repository")
    print("6. Exit")

def main():
    if not os.path.exists(REPOS_DIR):
        os.makedirs(REPOS_DIR)
    
    repos = load_repos()
    
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()
        
        if choice == '1':
            results = []
            for repo in repos:
                result = clone_repo(repo)
                results.append(result)
                print(json.dumps(result, indent=2))
            with open('changes_results.json', 'w') as f:
                json.dump(results, f, indent=2)
        
        elif choice == '2':
            results = []
            for repo in repos:
                result = update_repo(repo)
                results.append(result)
                print(json.dumps(result, indent=2))
            with open('changes_results.json', 'w') as f:
                json.dump(results, f, indent=2)
        
        elif choice == '3':
            summaries = []
            for repo in repos:
                summary = get_last_commit_summary(repo)
                summaries.append(summary)
                print(json.dumps(summary, indent=2))
        
        elif choice == '4':
            print("Available repositories:")
            for i, repo in enumerate(repos, 1):
                print(f"{i}. {repo}")
            try:
                idx = int(input("Select repository number: ")) - 1
                if 0 <= idx < len(repos):
                    view_commit_history(repos[idx])
                else:
                    print("Invalid number.")
            except ValueError:
                print("Invalid input.")
        
        elif choice == '5':
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
            break
        
        else:
            print("Invalid choice.")

if __name__ == '__main__':
    main()
