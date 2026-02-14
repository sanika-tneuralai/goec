"""
Centralized logging configuration for all modules.
"""
import logging
import sys
from pathlib import Path
from common.config import LOG_LEVEL, LOG_FORMAT, LOG_FILE


def setup_logger(name: str = __name__, log_file: str = LOG_FILE, level: str = LOG_LEVEL) -> logging.Logger:
    """
    Setup and configure logger with both file and console handlers.
    
    Args:
        name: Logger name (typically __name__)
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for a module.
    
    Args:
        name: Module name (use __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Default application logger
app_logger = setup_logger("app")

print("✓ logger module loaded")
