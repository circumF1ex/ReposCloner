"""Configuration management for ReposCloner"""

import os
import json
import logging
from typing import Dict

CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
    'repos_dir': './repos',
    'repos_file': 'repos.txt',
    'max_retries': 3,
    'retry_delay': 2,
    'max_workers': 4,
    'enable_logging': True,
    'log_file': 'reposcloner.log',
    'log_level': 'INFO',
    'auto_parallel': True,
    'default_commit_limit': 50,
    'language': 'ru',
    'debug': False,
}

def load_config() -> Dict:
    """Load configuration from config.json or use defaults"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**DEFAULT_CONFIG, **config}
        except Exception as e:
            print(f"Warning: Error loading config.json: {e}. Using defaults.")
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def is_debug_enabled(config: Dict = None) -> bool:
    """Hidden debug switch: env ``REPOSCLONER_DEBUG=1`` or ``debug: true`` in config."""
    env = os.environ.get('REPOSCLONER_DEBUG', '').strip().lower()
    if env in ('1', 'true', 'yes', 'on'):
        return True
    return bool((config or {}).get('debug', False))


def save_config(config: Dict, path: str = CONFIG_FILE) -> None:
    """Persist configuration (e.g. language chosen in the web console)."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def setup_logging(config: Dict) -> logging.Logger:
    """Setup logging based on configuration"""
    if config['enable_logging']:
        log_level = getattr(logging, config['log_level'].upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config['log_file'], encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
    else:
        logger = logging.getLogger(__name__)
        logger.addHandler(logging.NullHandler())
    
    return logger
