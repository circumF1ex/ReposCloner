import os
import subprocess
from pathlib import Path
from datetime import datetime

def list_repos():
    repos_dir = Path('repos')
    if not repos_dir.exists():
        print("Папка repos не найдена.")
        return []
    repos = [d.name for d in repos_dir.iterdir() if d.is_dir() and (d / '.git').exists()]
    return repos

def view_repo_commits(repo_name, limit=None, author=None):
    repo_path = Path('repos') / repo_name
    if not repo_path.exists():
        print(f"Репозиторий {repo_name} не найден.")
        return

    try:
        cmd = ['git', 'log', '--pretty=format:%h|%ad|%an|%s', '--date=iso']
        if author:
            cmd.extend(['--author', author])
        if limit:
            cmd.extend(['-n', str(limit)])
        
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)
        commits = [c for c in result.stdout.strip().split('\n') if c.strip()]
        if commits:
            print(f"\nКоммиты для {repo_name} ({len(commits)} commits):")
            print("=" * 100)
            print(f"{'#':<4} {'Hash':<8} {'Date':<20} {'Author':<25} {'Message'}")
            print("-" * 100)
            for i, commit_line in enumerate(commits, 1):
                parts = commit_line.split('|', 3)
                if len(parts) == 4:
                    hash_short, date_str, author_name, message = parts
                    try:
                        date_obj = datetime.fromisoformat(date_str.replace('+', '+').split('+')[0])
                        date_formatted = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        date_formatted = date_str[:19]
                    message_short = message[:60] + '...' if len(message) > 60 else message
                    print(f"{i:<4} {hash_short:<8} {date_formatted:<20} {author_name:<25} {message_short}")
            print("=" * 100)
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
            commits = [c for c in result.stdout.strip().split('\n') if c.strip()]
            if commits:
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

    print("\n" + "="*60)
    print("COMMIT VIEWER")
    print("="*60)
    print("Доступные репозитории:")
    for i, repo in enumerate(repos, 1):
        print(f"{i:2d}. {repo}")

    choice = input("\nВыберите репозиторий (номер) или введите 'user' для просмотра коммитов пользователя: ").strip()

    if choice.lower() == 'user':
        username = input("Введите имя пользователя: ").strip()
        view_user_commits_all_repos(username)
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(repos):
                limit_input = input("Лимит коммитов (Enter для всех): ").strip()
                limit = int(limit_input) if limit_input.isdigit() else None
                author_input = input("Фильтр по автору (Enter для всех): ").strip()
                author = author_input if author_input else None
                view_repo_commits(repos[idx], limit=limit, author=author)
            else:
                print("Неверный номер.")
        except ValueError:
            print("Неверный ввод.")

if __name__ == "__main__":
    main()
