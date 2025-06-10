import configparser
from typing import Optional, Dict
import os

def read_config(config_path: Optional[str] = None, modulename: Optional[str] = None) -> Dict:
    """load config file
    
    Args:
        config_path: config file path, if None, use environment variable CONFIG_PATH or default path
        modulename: config module name, if None, return the whole config
        
    Returns:
        Dict: config information
    """
    if config_path is None:
        config_path = os.getenv('CONFIG_PATH', 'config/config.ini')
    
    config = configparser.ConfigParser()
    config.read(config_path)
    return config[modulename] if modulename is not None else config