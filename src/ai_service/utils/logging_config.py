"""
Centralized logging configuration for AI Service
"""

import os
import logging
import logging.config
import yaml
from pathlib import Path
from typing import Optional


def setup_logging(
    config_path: Optional[str] = None,
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None
) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        config_path: Path to logging configuration YAML file
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
    """
    # Default paths
    if config_path is None:
        # Check if custom logging config is specified in environment
        if 'LOGGING_CONFIG' in os.environ:
            config_path = Path(os.environ['LOGGING_CONFIG'])
        else:
            config_path = Path(__file__).parent.parent / "config" / "logging.yml"
    
    if log_dir is None:
        # Check if we're running in Docker or locally
        if os.path.exists('/app'):
            log_dir = Path("/app/logs")
        else:
            # For local development, use current directory
            log_dir = Path.cwd() / "logs"
    
    # Create logs directory if it doesn't exist
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # Load configuration
    if Path(config_path).exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Update file paths to use absolute paths
            for handler_name, handler_config in config.get('handlers', {}).items():
                if 'filename' in handler_config:
                    filename = handler_config['filename']
                    if not os.path.isabs(filename):
                        handler_config['filename'] = str(log_dir / filename)
            
            # Override log level if specified
            if log_level:
                level = getattr(logging, log_level.upper(), logging.INFO)
                config['root']['level'] = level
                for logger_config in config.get('loggers', {}).values():
                    logger_config['level'] = level
            
            logging.config.dictConfig(config)
        except Exception as e:
            print(f"Warning: Failed to load logging config: {e}")
            # Fall through to basic config
    else:
        # Fallback to basic configuration
        logging.basicConfig(
            level=getattr(logging, log_level.upper() if log_level else 'INFO'),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Suppress third-party loggers
        logging.getLogger('langdetect').setLevel(logging.WARNING)
        logging.getLogger('spacy').setLevel(logging.WARNING)
        logging.getLogger('pymorphy3').setLevel(logging.WARNING)
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
        logging.getLogger('transformers').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with proper configuration
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_function_entry(logger: logging.Logger, func_name: str, **kwargs) -> None:
    """
    Log function entry with parameters
    
    Args:
        logger: Logger instance
        func_name: Function name
        **kwargs: Function parameters to log
    """
    if kwargs:
        params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.debug(f"Entering {func_name}({params})")
    else:
        logger.debug(f"Entering {func_name}()")


def log_function_exit(logger: logging.Logger, func_name: str, result=None) -> None:
    """
    Log function exit with result
    
    Args:
        logger: Logger instance
        func_name: Function name
        result: Function result to log
    """
    if result is not None:
        logger.debug(f"Exiting {func_name}() -> {type(result).__name__}")
    else:
        logger.debug(f"Exiting {func_name}()")


def log_error(logger: logging.Logger, error: Exception, context: str = "") -> None:
    """
    Log error with context
    
    Args:
        logger: Logger instance
        error: Exception instance
        context: Additional context information
    """
    error_msg = f"{type(error).__name__}: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    
    logger.error(error_msg, exc_info=True)


def log_performance(logger: logging.Logger, operation: str, duration: float) -> None:
    """
    Log performance metrics
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration: Duration in seconds
    """
    logger.info(f"Performance: {operation} completed in {duration:.3f}s")


class LoggingMixin:
    """
    Mixin class to add logging capabilities to any class
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(f"{self.__module__}.{self.__class__.__name__}")
        return self._logger
    
    def log_entry(self, method_name: str, **kwargs) -> None:
        """Log method entry"""
        log_function_entry(self.logger, method_name, **kwargs)
    
    def log_exit(self, method_name: str, result=None) -> None:
        """Log method exit"""
        log_function_exit(self.logger, method_name, result)
    
    def log_error(self, error: Exception, context: str = "") -> None:
        """Log error"""
        log_error(self.logger, error, context)
    
    def log_performance(self, operation: str, duration: float) -> None:
        """Log performance"""
        log_performance(self.logger, operation, duration)
