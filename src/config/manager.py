"""
Config Manager - Load and manage game configurations
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manage game configurations"""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize config manager
        
        Args:
            config_dir: Config directory
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
    
    def load_game_config(self, game_name_or_path: str) -> Optional[Dict[str, Any]]:
        """
        Load game configuration
        
        Args:
            game_name_or_path: Game name (for config/games/<name>.yaml) or full path to config file
        
        Returns:
            Game configuration dict or None if not found
        """
        # Check cache
        if game_name_or_path in self._cache:
            return self._cache[game_name_or_path]
        
        # Try as game name first (config/games/<name>.yaml)
        games_dir = Path("config/games")
        config_file = games_dir / f"{game_name_or_path}.yaml"
        
        # If not found, try as direct path
        if not config_file.exists():
            config_file = Path(game_name_or_path)
            if not config_file.is_absolute():
                config_file = Path(game_name_or_path)
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self._cache[game_name_or_path] = config
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
    
    def save_game_config(self, config_path: str, config: Dict[str, Any]) -> bool:
        """
        Save game configuration
        
        Args:
            config_path: Path to config file
            config: Configuration dict
        
        Returns:
            True if successful
        """
        config_file = Path(config_path)
        if not config_file.is_absolute():
            config_file = self.config_dir.parent / config_path
        
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            self._cache[str(config_path)] = config
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_template_path(self, template_name: str) -> Path:
        """
        Get path to template image
        
        Args:
            template_name: Name of the template image
        
        Returns:
            Path to template image
        """
        template_dir = Path("config/templates")
        return template_dir / template_name

