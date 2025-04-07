# igent/logging_config.py
import logging

import colorlog


# Custom formatter to handle matcher and critic colors
class CustomColoredFormatter(colorlog.ColoredFormatter):
    def format(self, record):
        msg = record.getMessage()
        if "matcher:" in msg:
            record.log_color = self.log_colors.get("MATCHER", "blue")
        elif "critic:" in msg:
            record.log_color = self.log_colors.get("CRITIC", "purple")
        else:
            record.log_color = self.log_colors.get(record.levelname, "green")
        return super().format(record)


# Configure a unified logger
def setup_logging(logger_name="igent"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create and configure a single colored handler
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        CustomColoredFormatter(
            "%(log_color)s%(levelname)s:%(name)s:%(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
                "FILE": "bg_yellow,bold",
                "MATCHER": "blue",
                "CRITIC": "purple",
            },
        )
    )

    logger.addHandler(handler)
    logger.propagate = False

    # Suppress external library logs
    logging.getLogger("autogen_core").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Add custom FILE level
    logging.addLevelName(60, "FILE")
    setattr(
        logger,
        "file",
        lambda message, *args, **kwargs: logger.log(60, message, *args, **kwargs),
    )

    return logger


# Singleton logger instance
logger = setup_logging()
