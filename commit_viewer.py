import os
import subprocess
from pathlib import Path

def list_repos():
    repos_dir = Path('repos')
    if not repos_dir.exists():
        print("Папка repos не найдена.")
        return []
    repos = [d.name for d in repos_dir.iterdir() if d.is_dir() and (d / '.git').exists()]
    return repos

def view_repo_commits(repo_name):
    repo_path = Path('repos') / repo_name
    if not repo_path.exists():
        print(f"Репозиторий {repo_name} не найден.")
        return

    try:
        result = subprocess.run(['git', 'log', '--pretty=format:%h %ad %s', '--date=iso'],
                                cwd=repo_path, capture_output=True, text=True, check=True)
        commits = result.stdout.strip().split('\n')
        if commits:
            print(f"Коммиты для {repo_name}:")
            for commit in commits:
                print(commit)
        else:
            print(f"Нет коммитов в {repo_name}.")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при получении коммитов: {e}")

def view_user_commits_all_repos(username):
    repos = list_repos()
    if not repos:
        return

    all_commits = []
    for repo in repos:
        repo_path = Path('repos') / repo
        try:
            result = subprocess.run(['git', 'log', '--author=' + username, '--pretty=format:%h %ad %s %D', '--date=iso'],
                                    cwd=repo_path, capture_output=True, text=True, check=True)
            commits = result.stdout.strip().split('\n')
            if commits and commits[0]:
                for commit in commits:
                    all_commits.append(f"{repo}: {commit}")
        except subprocess.CalledProcessError:
            pass  # Ignore repos with no commits by user

    if all_commits:
        print(f"Все коммиты пользователя {username} во всех репозиториях:")
        for commit in all_commits:
            print(commit)
    else:
        print(f"Нет коммитов пользователя {username}.")

def main():
    repos = list_repos()
    if not repos:
        print("Нет доступных репозиториев.")
        return

    print("Доступные репозитории:")
    for i, repo in enumerate(repos, 1):
        print(f"{i}. {repo}")

    choice = input("Выберите репозиторий (номер) или введите 'user' для просмотра коммитов пользователя: ").strip()

    if choice.lower() == 'user':
        username = input("Введите имя пользователя: ").strip()
        view_user_commits_all_repos(username)
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(repos):
                view_repo_commits(repos[idx])
            else:
                print("Неверный номер.")
        except ValueError:
            print("Неверный ввод.")

if __name__ == "__main__":
    main()
