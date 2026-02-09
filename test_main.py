import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from main import (load_repos, clone_repo, update_repo, get_last_commit_summary,
                  view_commit_history, reclone_repo, REPOS_DIR)

class TestMainFunctions(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_repos_dir = REPOS_DIR
        global REPOS_DIR
        REPOS_DIR = os.path.join(self.temp_dir, 'repos')
        os.makedirs(REPOS_DIR, exist_ok=True)

    def tearDown(self):
        shutil.rmtemp(self.temp_dir)
        global REPOS_DIR
        REPOS_DIR = self.old_repos_dir

    def test_load_repos(self):
        # Create a temp repos.txt
        repos_path = os.path.join(self.temp_dir, 'repos.txt')
        with open(repos_path, 'w') as f:
            f.write('repo1/user/repo\nrepo2/user/repo\n')
        
        repos = load_repos(repos_path)
        self.assertEqual(repos, ['repo1/user/repo', 'repo2/user/repo'])

    @patch('main.Repo')
    @patch('main.GitCommandError')
    def test_clone_repo_new(self, mock_error, mock_repo):
        mock_repo.clone_from.return_value = None
        result = clone_repo('test/user/repo')
        self.assertEqual(result['status'], 'cloned')
        mock_repo.clone_from.assert_called_once()

    @patch('main.os.path.exists')
    def test_clone_repo_already_exists(self, mock_exists):
        mock_exists.return_value = True
        result = clone_repo('test/user/repo')
        self.assertEqual(result['status'], 'already_cloned')

    @patch('main.Repo')
    @patch('main.GitCommandError')
    def test_clone_repo_error(self, mock_error, mock_repo):
        mock_repo.clone_from.side_effect = mock_error('Clone failed')
        result = clone_repo('test/user/repo')
        self.assertEqual(result['status'], 'error')
        self.assertIn('Clone failed', result['message'])

    @patch('main.Repo')
    def test_update_repo_not_cloned(self, mock_repo):
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            result = update_repo('test/user/repo')
            self.assertEqual(result['status'], 'not_cloned')

    @patch('main.Repo')
    def test_update_repo_no_changes(self, mock_repo):
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.head.commit.hexsha = 'abc123'
        mock_repo_instance.remotes.origin.pull.return_value = None
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = update_repo('test/user/repo')
            self.assertEqual(result['status'], 'no_changes')

    @patch('main.Repo')
    def test_update_repo_updated(self, mock_repo):
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.head.commit.hexsha = 'old'
        mock_repo_instance.remotes.origin.pull.return_value = None
        mock_repo_instance.head.commit.hexsha = 'new'  # Simulate change after pull
        mock_repo_instance.iter_commits.return_value = [MagicMock(hexsha='new', message='test', author=MagicMock(name='Author'))]
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = update_repo('test/user/repo')
            self.assertEqual(result['status'], 'updated')
            self.assertEqual(result['new_commits_count'], 1)

    @patch('main.Repo')
    @patch('main.GitCommandError')
    def test_update_repo_pull_error_force_update(self, mock_error, mock_repo):
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.head.commit.hexsha = 'old'
        mock_repo_instance.remotes.origin.pull.side_effect = mock_error('Pull failed')
        mock_repo_instance.git.fetch.return_value = None
        mock_repo_instance.active_branch.name = 'main'
        mock_repo_instance.git.reset.return_value = None
        mock_repo_instance.head.commit.hexsha = 'new'
        mock_repo_instance.iter_commits.return_value = [MagicMock(hexsha='new', message='test', author=MagicMock(name='Author'))]
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = update_repo('test/user/repo')
            self.assertEqual(result['status'], 'updated_forced')
            mock_repo_instance.git.reset.assert_called_with('--hard', 'origin/main')

    @patch('main.Repo')
    def test_get_last_commit_summary_not_cloned(self, mock_repo):
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            result = get_last_commit_summary('test/user/repo')
            self.assertEqual(result['status'], 'not_cloned')

    @patch('main.Repo')
    def test_get_last_commit_summary(self, mock_repo):
        mock_commit = MagicMock()
        mock_commit.hexsha = 'abc123'
        mock_commit.message = 'Test commit'
        mock_commit.author.name = 'Test Author'
        mock_commit.authored_datetime.isoformat.return_value = '2023-01-01T00:00:00'
        mock_repo_instance = MagicMock()
        mock_repo_instance.head.commit = mock_commit
        mock_repo.return_value = mock_repo_instance
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = get_last_commit_summary('test/user/repo')
            self.assertEqual(result['last_commit']['hash'], 'abc123')
            self.assertEqual(result['last_commit']['message'], 'Test commit')

    @patch('main.Repo')
    @patch('main.print')
    def test_view_commit_history_not_cloned(self, mock_print, mock_repo):
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = False
            view_commit_history('test/user/repo')
            mock_print.assert_called_with('Repository test/user/repo not cloned.')

    @patch('main.Repo')
    @patch('main.print')
    def test_view_commit_history(self, mock_print, mock_repo):
        mock_repo_instance = MagicMock()
        mock_commits = [MagicMock(hexsha='abc123', authored_datetime=MagicMock(isoformat=lambda: '2023-01-01'), author=MagicMock(name='Author'), message='Test')]
        mock_repo_instance.iter_commits.return_value = mock_commits
        mock_repo.return_value = mock_repo_instance
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            view_commit_history('test/user/repo')
            mock_print.assert_any_call('Commit history for test/user/repo:')
            mock_print.assert_any_call('abc123 2023-01-01 Author: Test')

    @patch('main.Repo')
    @patch('main.GitCommandError')
    def test_reclone_repo(self, mock_error, mock_repo):
        mock_repo.clone_from.return_value = None
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('main.shutil.rmtree') as mock_rmtree:
                result = reclone_repo('test/user/repo')
                self.assertEqual(result['status'], 'recloned')
                mock_rmtree.assert_called_once()
                mock_repo.clone_from.assert_called_once()

    @patch('main.shutil.rmtree')
    @patch('main.Repo')
    @patch('main.GitCommandError')
    def test_reclone_repo_error(self, mock_error, mock_repo, mock_rmtree):
        mock_repo.clone_from.side_effect = mock_error('Reclone failed')
        with patch('main.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = reclone_repo('test/user/repo')
            self.assertEqual(result['status'], 'error')
            self.assertIn('Reclone failed', result['message'])

if __name__ == '__main__':
    unittest.main()
