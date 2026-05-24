from nexus.core.trackers.logging_utils import DummyLogger


def base(logger=None, title=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            local_logger = logger if logger is not None else DummyLogger()
            local_title = title if title is not None else ""

            if title is not None:
                local_logger.info(f"Running: {local_title}")

            return func(*args, **kwargs)


        return wrapper
    return decorator
