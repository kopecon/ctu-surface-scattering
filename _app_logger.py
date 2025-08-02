# Libraries to work with the operating system
from pathlib import Path
import sys
import time
from typing import Callable
from functools import wraps
import inspect


# Log handling
import logging.config
import json

import _parameters as param


logger = logging.getLogger('log_this')
spacing_multiplier = 4


class NonErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        return record.levelno <= logging.INFO


def create_logs_folder() -> None:
    """
    This function creates a "logs" folder in the root.

    :return: None.
    """

    # Creates the "logs" folder at the content root if it already does not exist
    Path.mkdir(param.logs_folder_path, exist_ok=True)


def create_logging_configs_folder() -> None:
    """
    This function creates a "logging_configs" folder in the root.

    :return: None.
    """

    # Creates the "logging_configs" folder at the content root if it already does not exist
    Path.mkdir(param.logging_configs_path, exist_ok=True)


def generate_default_log_config_file() -> None:
    output_path = param.logging_configs_path / param.default_log_config

    # Skip generating of the file if it already exists
    if output_path.exists():
        pass

    settings = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(levelname)s: %(message)s"
            },
            "detailed": {
                "format": "[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z"
            }
        },
        "filters": {
            "no_errors": {
                "()": "_app_logger.NonErrorFilter"
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
                "filters": ["no_errors"]
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "simple",
                "stream": "ext://sys.stderr"
            },

            "file_debug": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": f"{param.logs_folder_path}/debug.log",
                "encoding": "utf-8",
                "maxBytes": param.logger_max_size,
                "backupCount": param.logger_backup_count,
                "mode": "a"
            },
            "file_info": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": f"{param.logs_folder_path}/info.log",
                "encoding": "utf-8",
                "maxBytes": param.logger_max_size,
                "backupCount": param.logger_backup_count,
                "mode": "a",
                "filters": ["no_errors"]

            }
        },
        "loggers": {
            # Suppress font_manager debug messages
            "matplotlib.font_manager": {
                "level": "WARNING",  # suppress DEBUG and INFO from font_manager
                "handlers": ["file_debug"],
                "propagate": False
            },
            "root": {
                "level": "DEBUG",
                "handlers": [
                    "stderr",
                    "stdout",
                    "file_debug",
                    "file_info"
                ]
            }
        }
    }
    with open(f'{output_path}', 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)


def setup_logging(config_file_path=param.logger_config_path) -> None:
    """
    This function configures our app logger with provided configuration in the .json config file
    (Path to the .json file is defined in "hardcoded_parameters")

    :param config_file_path: Path to the .json config file
    :return: None.
    """
    create_logs_folder()  # Prepare the logs folder to save our files to
    create_logging_configs_folder()
    generate_default_log_config_file()

    if config_file_path.exists():
        # Load the .json config file
        with open(config_file_path) as f_in:
            config = json.load(f_in)

        # Configure the logger with the loaded .json file
        logging.config.dictConfig(config)

    else:
        # In case the log config file has not been provided, introduce a simple logger
        # Under normal circumstances, these settings are not used.
        logging.basicConfig(filename=f'logs/temp.log', level=logging.DEBUG)
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        logger.error(f"{log_this.space}Missing logger config file: {config_file_path}.")


# Decorator
def log_this(function: Callable) -> Callable:
    """
    This is a wrapper that can be used as a decorator above a function declaration like this: @log_this .
    If used as a decorator, the function is going to be logged with the provided wrapper bellow.
    The wrapper consists of two log messages:

    1) Start of the function
    2) End of the function [execution time].

    log_this has three attributes (like an object):
        * **log_this.counter (int)**: Counts, how many times a logging of a function has been called. It is used to count how many white spaces before a log message is supposed to be to map the nested hierarchy of function calling. Increases everytime a logged function is called and decrease every time the logged function is resolved.
        * **log_this.space (str)**: The amount of white spaces before the log message. Used when writing log messages outside of log_this wrapper, but maintaining the space hierarchy.
        * **log_this.target (str)**: When the logged function is called, the logger writes the name of the function, but for the clarity of the log, log_this.target provides the information of for what the function was called for. For example the locality of the currently processed file.

    :param function: The function to be logged.
    :return: The wrapped function.
    """
    def _get_log_space() -> str:
        """
        This function calculates how much whitespace should be before the text starts to intend the nested functions.
        :return: None.
        """
        return " " * log_this.counter * spacing_multiplier

    @wraps(function)
    def wrap(*args, **kwargs):
        caller = inspect.currentframe().f_locals['args'][0]  # Get the name of the object which called the function.
        log_this.counter += 1
        log_this.space = _get_log_space() * 2

        logger.info(f'{_get_log_space()}Starting "{function.__name__}" for: {caller}...')

        start_time = time.time()
        result = function(*args, **kwargs)  # Run the function
        end_time = time.time()
        duration = abs(end_time-start_time)

        logger.info(f'{_get_log_space()}Finished "{function.__name__}" for: {caller} [{round(duration, 3)} s]')
        log_this.counter -= 1

        return result

    return wrap


log_this.counter = 0
log_this.space = ''
