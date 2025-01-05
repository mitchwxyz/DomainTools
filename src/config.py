import configparser
from pathlib import Path

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        # Load default config from project root
        project_root = Path(__file__).parent.parent
        default_config_path = project_root / 'config' / 'default.ini'
        self.config.read(default_config_path)

        # Load user config if exists
        user_config_path = Path.home() / '.config' / 'jsonld-scraper' / 'config.ini'
        if user_config_path.exists():
            self.config.read(user_config_path)

    def get(self, section: str, key: str) -> str:
        return self.config.get(section, key)

    def getint(self, section: str, key: str) -> int:
        return self.config.getint(section, key)

    def getfloat(self, section: str, key: str) -> float:
        return self.config.getfloat(section, key)