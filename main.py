import os
import sys
import shutil
import time
from git import Repo, GitCommandError
import json

# Папка для локального хранения репозиториев
REPOS_DIR = './repos'

def clone_or_pull_repo(repo_name):
    repo_path = os.path.join(REPOS_DIR, repo_name.replace('/', '_'))
    if os.path.exists(repo_path):
        # Репозиторий уже клонирован — делаем pull
        try:
            repo = Repo(repo_path)
            # Получаем хэш последнего коммита до pull
            old_commit = repo.head.commit.hexsha
            # Делаем pull
            origin = repo.remotes.origin
            origin.pull()
            # Получаем хэш после pull
            new_commit = repo.head.commit.hexsha
            if old_commit != new_commit:
                # Есть изменения — получаем новые коммиты
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
            error_message = str(e)
            if "untracked working tree files would be overwritten" in error_message:
                # Разрешаем ошибку: делаем fetch и reset --hard для принудительного обновления
                try:
                    repo.git.fetch()
                    current_branch = repo.active_branch.name
                    repo.git.reset('--hard', f'origin/{current_branch}')
                    new_commit = repo.head.commit.hexsha
                    if old_commit != new_commit:
                        # Есть изменения — получаем новые коммиты
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
                    changes = {'repo': repo_name, 'status': 'error', 'message': f"Failed to resolve untracked files error: {str(e2)}"}
            elif "invalid path" in error_message:
                # Разрешаем ошибку с недопустимым путём: сначала пытаемся fetch и reset --hard
                try:
                    repo.git.fetch()
                    current_branch = repo.active_branch.name
                    repo.git.reset('--hard', f'origin/{current_branch}')
                    new_commit = repo.head.commit.hexsha
                    if old_commit != new_commit:
                        # Есть изменения — получаем новые коммиты
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
                    # Если reset тоже падает с invalid path, удаляем локальный репозиторий и клонируем заново
                    try:
                        # Пытаемся удалить папку с повторными попытками (на случай блокировки файлов)
                        for attempt in range(3):
                            try:
                                shutil.rmtree(repo_path)
                                break
                            except OSError as e3:
                                if attempt < 2:
                                    time.sleep(1)  # Ждём 1 секунду перед повтором
                                else:
                                    raise e3
                        Repo.clone_from(f'https://github.com/{repo_name}.git', repo_path)
                        changes = {'repo': repo_name, 'status': 'recloned'}
                    except Exception as e3:
                        changes = {'repo': repo_name, 'status': 'error', 'message': f"Failed to resolve invalid path error after recloning: {str(e3)}"}
            else:
                changes = {'repo': repo_name, 'status': 'error', 'message': error_message}
    else:
        # Клонируем репозиторий
        try:
            Repo.clone_from(f'https://github.com/{repo_name}.git', repo_path)
            changes = {'repo': repo_name, 'status': 'cloned'}
        except GitCommandError as e:
            changes = {'repo': repo_name, 'status': 'error', 'message': str(e)}
    return changes

def main(repos_file):
    if not os.path.exists(REPOS_DIR):
        os.makedirs(REPOS_DIR)
    
    with open(repos_file, 'r') as f:
        repos = [line.strip() for line in f if line.strip()]
    
    results = []
    for repo in repos:
        result = clone_or_pull_repo(repo)
        results.append(result)
        print(json.dumps(result, indent=2))
    
    # Сохранить результаты в файл
    with open('changes_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python clone_and_pull_repos.py <repos_file>")
        sys.exit(1)
    main(sys.argv[1])
