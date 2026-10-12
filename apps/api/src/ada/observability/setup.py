import logging

from ada.config import settings


def init():
    logging.basicConfig(level=logging.INFO,
                        format='{"t":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}')
    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.app_env)
