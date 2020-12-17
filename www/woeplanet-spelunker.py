# pylint: disable=no-member

import logging
from spelunker import app

if __name__ == '__main__':
    app.run()

else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
