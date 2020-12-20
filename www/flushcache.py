#!/usr/bin/env python

import flask_caching
import os

from spelunker import app

cache = flask_caching.Cache()

def main():
    cache.init_app(app, config={
        'CACHE_TYPE': 'filesystem',
        'CACHE_DEFAULT_TIMEOUT': 5,
        'CACHE_IGNORE_ERRORS': False,
        'CACHE_DIR': os.environ.get('WOE_CACHE_DIR'),
        'CACHE_THRESHOLD': 500,
        'CACHE_OPTIONS': {
            'mode': int(os.environ.get('WOE_CACHE_MASK'))
        }
    })
    
    with app.app_context():
        cache.clear()
        
if __name__ == '__main__':
    main()
