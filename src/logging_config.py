"""
Centralized Logging Configuration
Provides consistent logging across all modules
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

def setup_logging(
    log_level='INFO',
    log_file='data/logs/pipeline.log',
    max_bytes=10485760,  # 10MB
    backup_count=5
):
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File Handler with rotation (all levels)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error File Handler (ERROR and above only)
    error_log_file = log_path.parent / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    # Log startup
    logger.info("="*60)
    logger.info("Logging initialized")
    logger.info(f"Log level: {log_level}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*60)
    
    return logger

def get_logger(name):
    """Get a logger with the specified name"""
    return logging.getLogger(name)

class LoggerMixin:
    """Mixin class to add logging capability to any class"""
    
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger

# Context manager for logging execution time
class LogExecutionTime:
    """Context manager to log execution time of code blocks"""
    
    def __init__(self, operation_name, logger=None):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(
                f"Completed: {self.operation_name} "
                f"(Duration: {duration:.2f}s)"
            )
        else:
            self.logger.error(
                f"Failed: {self.operation_name} "
                f"(Duration: {duration:.2f}s) - {exc_val}"
            )
        
        return False  # Don't suppress exceptions

# Decorator for logging function execution
def log_execution(func):
    """Decorator to log function execution"""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        func_name = f"{func.__module__}.{func.__name__}"
        
        logger.debug(f"Calling: {func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed: {func_name}")
            return result
        except Exception as e:
            logger.error(f"Error in {func_name}: {str(e)}", exc_info=True)
            raise
    
    return wrapper

# Example usage in other modules:
# from logging_config import setup_logging, get_logger, LogExecutionTime, log_execution
# 
# # In main.py or __init__.py
# setup_logging(log_level='INFO')
# 
# # In any module
# logger = get_logger(__name__)
# logger.info("This is a log message")
# 
# # Using context manager
# with LogExecutionTime("Data Loading", logger):
#     # Your code here
#     pass
# 
# # Using decorator
# @log_execution
# def my_function():
#     pass