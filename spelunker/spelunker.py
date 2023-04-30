#!/usr/bin/env python
# pylint: disable=too-many-lines
"""
A simple Flask based spelunker for visualising, poking into and querying WoePlanet data
"""

# gunicorn spelunker.spelunker:app --bind $(hostname):8888 -w 2 --log-level debug

import collections
import json
import logging
import os
import random
import re
import time
import urllib

import dotenv
import flask
import flask_caching
import inflect
import iso639

from woeplanet.utils import uri

from spelunker.querymanager import QueryManager

dotenv.load_dotenv(dotenv.find_dotenv())
template_dir = os.path.abspath('./templates')
static_dir = os.path.abspath('./static')
app = flask.Flask(__name__, template_folder=template_dir, static_folder=static_dir)

if __name__ != '__main__':
    logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = logger.handlers
    app.logger.setLevel(level=logger.level)

cache = flask_caching.Cache(
    config={
        'CACHE_TYPE': 'FileSystemCache',
        'CACHE_DEFAULT_TIMEOUT': 5,
        'CACHE_IGNORE_ERRORS': False,
        'CACHE_DIR': os.environ.get('WOE_CACHE_DIR'),
        'CACHE_THRESHOLD': 500,
        'CACHE_OPTIONS': {
            'mode': int(os.environ.get('WOE_CACHE_MASK'),
                        8)
        }
    }
)
cache.init_app(app)


@app.template_filter()
def commafy(value: int) -> str:
    """
    Custom template filter: comma-fy an integer
    """
    return f'{value:,}'


@app.template_filter()
def anyfy(value):
    """
    Custom template filter: a vs. an
    """
    return flask.g.inflect.an(value)


@app.template_filter()
def pluralise(value, count):
    """
    Custom template filter: pluralise a value
    """
    return flask.g.inflect.plural(value, count)


@app.errorhandler(404)
def page_not_found(error):
    """
    Error handler: 404
    """
    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        }
    }
    _query, _params, rsp = do_search(**params)
    if rsp['ok']:
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)

        sidebar_woeid = int(rows[0].get('woe:id'))
        sidebar_name = rows[0]['inflated'].get('name')

        template_args = {
            'map': True,
            'title': f'404 Hic Sunt Dracones : {error.code} {error.name}',
            'woeid': sidebar_woeid,
            'name': sidebar_name,
            'doc': rows[0]
        }
        template_args = get_geometry(rows[0], template_args)
        return flask.render_template('404.html.jinja', **template_args), 404

    return None, None


@app.errorhandler(500)
@app.errorhandler(503)
def internal_server_error(error):
    """
    Error handler: 5xx
    """
    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        }
    }
    _query, _params, rsp = do_search(**params)
    if rsp['ok']:
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)

        sidebar_woeid = int(rows[0].get('woe:id'))
        sidebar_name = rows[0]['inflated'].get('name')

        template_args = {
            'map': True,
            'title': f'{error.code} {error.name}',
            'error': error,
            'woeid': sidebar_woeid,
            'name': sidebar_name,
            'doc': rows[0]
        }
        template_args = get_geometry(rows[0], template_args)
        return flask.render_template('500.html.jinja', **template_args), error.code

    return None, None


@app.before_request
def init():
    """
    Initialisation/setup handler
    """

    es_host = os.environ.get('WOE_ES_HOST', 'localhost')
    es_port = os.environ.get('WOE_ES_PORT', '9200')
    es_docidx = os.environ.get('WOE_ES_DOC_INDEX', 'woeplanet')
    es_ptidx = os.environ.get('WOE_ES_PT_INDEX', 'placetypes')

    flask.g.docidx = es_docidx
    flask.g.ptidx = es_ptidx
    flask.g.inflect = inflect.engine()
    flask.g.inflect.defnoun('miscellaneous', 'miscellaneous')
    flask.g.inflect.defnoun('county', 'counties')
    flask.g.docmgr = QueryManager(host=es_host, port=es_port, index=es_docidx)
    flask.g.ptmgr = QueryManager(host=es_host, port=es_port, index=es_ptidx)
    flask.g.nearby_radius = '1km'
    flask.g.queryparams = get_queryparams()


@app.route('/', methods=['GET'])
@cache.cached(timeout=60)
def home_page():
    """
    Page handler: default landing page
    """

    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        }
    }

    _query, _params, rsp = do_search(**params)

    if rsp['ok']:
        woeid = int(rsp['rows'][0]['woe:id'])
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)
        doc = rows[0]
        template_args = {
            'map': True,
            'title': 'Home',
            'woeid': woeid,
            'name': doc['inflated']['name'],
            'doc': doc
        }
        template_args = get_geometry(doc, template_args)
        return flask.render_template('home.html.jinja', **template_args)

    return None, None


@app.route('/up', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """

    return {
        'status': 200,
        'message': 'OK'
    }


@app.route('/about/', methods=['GET'])
def about_page():
    """
    Page handler: about page
    """

    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        },
        'source': {
            'includes': [
                'woe:latitude',
                'woe:longitude',
                'woe:min_latitude',
                'woe:min_longitude',
                'woe:max_latitude',
                'woe:max_longitude',
                'woe:name',
                'woe:id',
                'woe:hierarchy',
                'iso:country',
                'woe:bbox',
                'woe:centroid',
                'geom:bbox',
                'geom:centroid'
            ]
        }
    }
    _query, _params, rsp = do_search(**params)
    if rsp['ok']:
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)
        name = rows[0]['inflated']['name']
        doc = rows[0]

        template_args = {
            'map': True,
            'title': 'About',
            'woeid': doc['woe:id'],
            'iso': doc.get('iso:country',
                           'GB'),
            'nearby': doc['woe:id'],
            'name': name,
            'doc': doc
        }
        template_args = get_geometry(doc, template_args)
        return flask.render_template('about.html.jinja', **template_args)

    return None, None


@app.route('/credits/', methods=['GET'])
@cache.cached(timeout=60)
def credits_page():
    """
    Page handler: credits page
    """

    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        }
    }
    _query, _params, rsp = do_search(**params)
    if rsp['ok']:
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)
        name = rows[0]['inflated']['name']

        template_args = {
            'map': True,
            'title': 'Credits',
            'woeid': rows[0]['woe:id'],
            'name': name,
            'doc': rows[0]
        }
        template_args = get_geometry(rows[0], template_args)
        return flask.render_template('credits.html.jinja', **template_args)

    return None, None


@app.route('/countries/', methods=['GET'])
@cache.cached(timeout=60)
def countries_page():
    """
    Page handler: countries page
    """

    includes, excludes = excludify()
    params = {
        'size': 0,
        'exclude': excludes,
        'facets': {
            'countries': True
        }
    }
    query, _params, rsp = do_search(**params)

    if rsp['ok']:
        totals = {
            'docs': rsp['pagination']['total'],
            'countries': len(rsp['facets']['countries']['buckets'])
        }
        buckets = rsp['facets']['countries']['buckets']
        for idx, country in enumerate(buckets):
            params = {
                'iso': country['key'],
                'include': {
                    'placetypes': [12]
                },
                'exclude': excludes,
                'source': {
                    'includes': ['woe:name',
                                 'iso:country']
                }
            }
            _query, _params, rsp = do_search(**params)
            if rsp['ok']:
                if country['key'] == 'ZZ':
                    buckets[idx]['name'] = 'Sorry, the world is a complicated place'
                elif country['key'] == 'XS':
                    buckets[idx]['name'] = 'Serbia'
                else:
                    buckets[idx]['name'] = rsp['rows'][0]['woe:name']

        params = {
            'size': 1,
            'random': True,
            'include': {
                'centroid': True
            },
            'exclude': {
                'placetypes': [0,
                               11,
                               25],
                'nullisland': True,
                'deprecated': True
            }
        }

        _query, _params, res = do_search(**params)
        if res['ok']:
            args = {
                'name': True
            }
            woeid = int(res['rows'][0]['woe:id'])
            rows = inflatify(res['rows'], **args)
            name = rows[0]['inflated']['name']

            template_args = {
                'map': True,
                'title': 'Countries',
                'total': totals,
                'buckets': buckets,
                'doc': rows[0],
                'woeid': woeid,
                'name': name,
                'es_query': trim_query(query),
                'includes': includes if includes else None,
                'took': rsp['took_sec']
            }
            template_args = get_geometry(rows[0], template_args)
            return flask.render_template('countries.html.jinja', **template_args)

    return None, None


@app.route('/country/<string:iso>/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def country_page(iso):
    """
    Page handler: country by ISO code page
    """

    iso = iso.upper()
    params = {
        'iso': iso,
        'exclude': {
            'placetype': [0,
                          12],
            'nullisland': True,
            'deprecated': True
        },
        'facets': {
            'placetypes': True
        }
    }
    placetype_name = get_str('placetype')
    placetype_name = get_single(placetype_name)
    if placetype_name:
        _query, placetype = get_pt_by_name(placetype_name)
        if placetype:
            params['include'] = {
                'placetypes': [int(placetype['id'])]
            }

    _query, _params, rsp = do_search(**params)
    if not rsp['ok']:
        flask.abort(404)

    if rsp['pagination']['total'] > 0:
        sidebar_woeid = int(rsp['rows'][0]['woe:id'])
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)
        sidebar_name = rows[0]['inflated']['name']
        doc = rows[0]

    else:
        rows = []
        params = {
            'size': 1,
            'random': True,
            'include': {
                'centroid': True
            },
            'exclude': {
                'placetypes': [0,
                               11,
                               25],
                'nullisland': True,
                'deprecated': True
            }
        }

        _query, _params, res = do_search(**params)
        if res['ok']:
            args = {
                'name': True
            }
            sidebar_woeid = int(res['rows'][0]['woe:id'])
            rows = inflatify(res['rows'], **args)
            sidebar_name = rows[0]['inflated']['name']
            doc = rows[0]

    template_args = {
        'map': True,
        'title': f'Child places for {iso}',
        'iso': iso,
        'results': rows,
        'woeid': sidebar_woeid,
        'name': sidebar_name,
        'doc': doc,
        'pagination': build_pagination_urls(pagination=rsp['pagination']),
        'facets': rsp['facets'] if 'facets' in rsp else []
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('results.html.jinja', **template_args)


@app.route('/id/<int:woeid>/', methods=['GET'])
@cache.cached(timeout=60)
def place_page(woeid):
    """
    Page handler: place by WOEID page
    """

    _query, doc = get_by_id(woeid)
    if not doc:
        flask.abort(404)

    _query, placetype = get_pt_by_id(doc['woe:placetype'])
    args = {
        'name': True,
        'hierarchy': True,
        'adjacencies': True,
        'aliases': True,
        'children': True
    }
    doc = inflatify(doc, **args)

    template_args = {
        'map': True,
        'title': f"WOEID {doc['woe:id']} ({doc['woe:name'] if 'woe:name' in doc else 'Unknown'})",
        'lang': get_language(doc['woe:lang']) if 'woe:lang' in doc else 'Unknown',
        'name': doc['woe:name'] if 'woe:name' in doc else 'Unknown',
        'placetype': placetype,
        'doc': doc,
        'urls': make_source_urls(doc)
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('place.html.jinja', **template_args)


@app.route('/id/<int:woeid>/map/', methods=['GET'])
@cache.cached(timeout=60)
def place_map_page(woeid):
    """
    Page handler: map by WOEID page
    """

    _query, doc = get_by_id(woeid)
    if not doc:
        flask.abort(404)

    _query, placetype = get_pt_by_id(doc['woe:placetype'])

    args = {
        'name': True,
        'hierarchy': True,
        'adjacencies': True,
        'aliases': True,
        'children': True
    }
    doc = inflatify(doc, **args)

    url = flask.url_for('place_page', woewoeid=id)
    name = doc['woe:name']
    popup = f'<h2>This is <a href="{url}">{name}</a></h2>'

    place_name = doc['woe:name'] if 'woe:name' in doc else 'Unknown'
    template_args = {
        'map': True,
        'title': f'WOEID {woeid} ({place_name}) | Map',
        'name': place_name,
        'woeid': woeid,
        'placetype': placetype,
        'doc': doc,
        'popup': popup,
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('map.html.jinja', **template_args)


@app.route('/id/<int:woeid>/nearby/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def nearby_id_page(woeid):
    """
    Nearby place page handler
    """

    _query, doc = get_by_id(woeid)
    if not doc:
        flask.abort(404)

    args = {
        'name': True
    }
    doc = inflatify(doc, **args)
    nearby_name = doc['inflated']['name']
    nearby_id = woeid

    radius = get_float('radius')
    radius = get_single(radius)
    if not radius:
        radius = flask.g.nearby_radius

    coords = [0, 0]
    if 'woe:centroid' in doc:
        coords = doc['woe:centroid']
    elif 'geom:centroid' in doc:
        coords = doc['geom:centroid']

    params = {
        'nearby': {
            'radius': radius,
            'coordinates': coords
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        },
        'facets': {
            'placetypes': True,
            'countries': False
        }
    }

    placetype_name = get_str('placetype')
    placetype_name = get_single(placetype_name)
    if placetype_name:
        _query, placetype = get_pt_by_name(placetype_name)
        if placetype:
            params['include'] = {
                'placetypes': [int(placetype['id'])]
            }

    query, _params, rsp = do_search(**params)
    if not rsp['ok']:
        flask.abort(404)

    if rsp['pagination']['total'] > 0:
        sidebar_woeid = int(rsp['rows'][0]['woe:id'])
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)
        sidebar_name = rows[0]['inflated']['name']
        doc = rows[0]

    else:
        rows = []
        params = {
            'size': 1,
            'random': True,
            'include': {
                'centroid': True
            },
            'exclude': {
                'placetypes': [0,
                               11,
                               25],
                'nullisland': True,
                'deprecated': True
            }
        }

        _query, _params, res = do_search(**params)
        res = flask.g.docmgr.single_rsp(res, **params)
        if res['ok']:
            args = {
                'name': True
            }
            sidebar_woeid = int(res['row']['woe:id'])
            row = inflatify(res['row'], **args)
            sidebar_name = row['inflated']['name']
            doc = row

    template_args = {
        'map': True,
        'title': f'Places near {sidebar_name}',
        'nearby_name': nearby_name,
        'nearby_id': nearby_id,
        'results': rows,
        'woeid': sidebar_woeid,
        'name': sidebar_name,
        'doc': doc,
        'pagination': build_pagination_urls(pagination=rsp['pagination']),
        'facets': rsp['facets'] if 'facets' in rsp else [],
        'es_query': trim_query(query),
        'took': rsp['took_sec']
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('results.html.jinja', **template_args)


@app.route('/nearby/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def nearby_page():
    """
    Nearby places page handler
    """

    lat = get_float('lat')
    lat = get_single(lat)
    lng = get_float('lng')
    lng = get_single(lng)

    if lat and lng:
        radius = get_float('radius')
        radius = get_single(radius)
        if not radius:
            radius = flask.g.nearby_radius

        coords = [lng, lat]
        params = {
            'nearby': {
                'radius': radius,
                'coordinates': coords
            },
            'exclude': {
                'placetypes': [0,
                               11,
                               25],
                'nullisland': True,
                'deprecated': True
            },
            'facets': {
                'placetypes': True,
                'countries': False
            }
        }

        placetype_name = get_str('placetype')
        placetype_name = get_single(placetype_name)
        if placetype_name:
            _query, placetype = get_pt_by_name(placetype_name)
            if placetype:
                params['include'] = {
                    'placetypes': [int(placetype['id'])]
                }

        query, _params, rsp = do_search(**params)
        if rsp['ok']:
            if rsp['pagination']['total'] > 0:
                sidebar_woeid = int(rsp['rows'][0]['woe:id'])
                args = {
                    'name': True
                }
                rows = inflatify(rsp['rows'], **args)
                sidebar_name = rows[0]['inflated']['name']
                doc = rows[0]

            else:
                rows = []
                params = {
                    'size': 1,
                    'random': True,
                    'include': {
                        'centroid': True
                    },
                    'exclude': {
                        'placetypes': [0,
                                       11,
                                       25],
                        'nullisland': True,
                        'deprecated': True
                    }
                }

                _query, _params, res = do_search(**params)
                res = flask.g.docmgr.single_rsp(res, **params)
                if res['ok']:
                    args = {
                        'name': True
                    }
                    sidebar_woeid = int(res['row']['woe:id'])
                    row = inflatify(res['row'], **args)
                    sidebar_name = row['inflated']['name']
                    doc = row

            template_args = {
                'map': True,
                'title': 'Places near me',
                'nearby_lat': lat,
                'nearby_lng': lng,
                'nearby_id': sidebar_woeid,
                'results': rows,
                'woeid': sidebar_woeid,
                'name': sidebar_name,
                'doc': doc,
                'pagination': build_pagination_urls(pagination=rsp['pagination']),
                'facets': rsp['facets'] if 'facets' in rsp else [],
                'es_query': trim_query(query),
                'took': rsp['took_sec']
            }
            template_args = get_geometry(doc, template_args)
            return flask.render_template('results.html.jinja', **template_args)

    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        }
    }

    _query, _params, res = do_search(**params)
    if res['ok']:
        args = {
            'name': True
        }
        sidebar_woeid = int(res['rows'][0]['woe:id'])
        row = inflatify(res['rows'][0], **args)
        sidebar_name = row['inflated']['name']
        doc = row

    template_args = {
        'map': True,
        'title': 'Places near me',
        'nearby_lat': lat,
        'nearby_lng': lng,
        'nearby_id': sidebar_woeid,
        'results': row,
        'woeid': sidebar_woeid,
        'name': sidebar_name,
        'doc': doc,
        'pagination': build_pagination_urls(pagination=res['pagination']),
        'facets': res['facets'] if 'facets' in res else []
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('nearby.html.jinja', **template_args)


@app.route('/nullisland/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def nullisland_page():
    """
    Null Island page handler
    """

    params = {
        'include': {
            'nullisland': True
        },
        'facets': {
            'placetypes': True
        }
    }
    placetype_name = get_str('placetype')
    placetype_name = get_single(placetype_name)
    if placetype_name:
        _query, placetype = get_pt_by_name(placetype_name)
        if placetype:
            params['include']['placetypes'] = [int(placetype['id'])]

    query, _params, rsp = do_search(**params)
    if not rsp['ok']:
        flask.abort(404)

    args = {
        'name': True
    }
    woeid = int(rsp['rows'][0]['woe:id'])
    rows = inflatify(rsp['rows'], **args)
    name = rows[0]['inflated']['name']

    template_args = {
        'map': True,
        'title': 'Places visiting Null Island',
        'nullisland': True,
        'doc': rows[0],
        'results': rows,
        'woeid': woeid,
        'name': name,
        'pagination': build_pagination_urls(pagination=rsp['pagination']),
        'facets': rsp['facets'] if 'facets' in rsp else [],
        'es_query': trim_query(query),
        'took': rsp['took_sec']
    }
    template_args = get_geometry(rows[0], template_args)
    return flask.render_template('results.html.jinja', **template_args)


@app.route('/placetypes/', methods=['GET'])
@cache.cached(timeout=60)
def placetypes_page():
    """
    Placetypes page handler
    """

    includes, excludes = excludify()
    params = {
        'size': 0,
        'exclude': excludes,
        'facets': {
            'placetypes': True
        }
    }
    query, _params, rsp = do_search(**params)
    if not rsp['ok']:
        flask.abort(404)

    totals = {
        'docs': rsp['pagination']['total'],
        'placetypes': len(rsp['facets']['placetypes']['buckets'])
    }
    buckets = rsp['facets']['placetypes']['buckets']

    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        }
    }

    _query, _params, res = do_search(**params)
    if not rsp['ok']:
        flask.abort(404)

    args = {
        'name': True
    }
    woeid = int(res['rows'][0]['woe:id'])
    rows = inflatify(res['rows'], **args)
    name = rows[0]['inflated']['name']

    template_args = {
        'map': True,
        'title': 'Placetypes',
        'total': totals,
        'buckets': buckets,
        'doc': rows[0],
        'woeid': woeid,
        'name': name,
        'es_query': trim_query(query),
        'includes': includes if includes else None,
        'took': rsp['took_sec']
    }
    template_args = get_geometry(rows[0], template_args)
    return flask.render_template('placetypes.html.jinja', **template_args)


@app.route('/placetype/<string:placetype_name>/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def placetype_page(placetype_name):
    """
    Placetype page handler
    """

    _query, placetype = get_pt_by_name(placetype_name)
    if not placetype:
        flask.abort(404)

    ptid = placetype['id']
    includes, excludes = excludify()
    params = {
        'include': {
            'placetypes': [ptid]
        },
        'exclude': excludes,
        'facets': {
            'placetypes': True,
            'countries': True,
        }
    }
    query, _params, rsp = do_search(**params)
    if not rsp['ok']:
        flask.abort(404)

    if rsp['pagination']['total'] > 0:
        sidebar_woeid = int(rsp['rows'][0]['woe:id'])
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)
        sidebar_name = rows[0]['inflated']['name']
        doc = rows[0]

    template_args = {
        'map': True,
        'title': f'Search results for placetype "{placetype_name}"',
        'results': rows,
        'woeid': sidebar_woeid,
        'name': sidebar_name,
        'doc': doc,
        'placetype': placetype,
        'pagination': build_pagination_urls(pagination=rsp['pagination']),
        'facets': rsp['facets'] if 'facets' in rsp else [],
        'includes': includes if includes else None,
        'es_query': trim_query(query)
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('results.html.jinja', **template_args)


@app.route('/random/', methods=['GET'])
def random_page():
    """
    Random WOEID page handler
    """

    params = {
        'size': 1,
        'random': True,
        'search': {},
        'include': {},
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        },
        'facets': {
            'placetypes': False,
            'countries': False
        }
    }
    _query, _params, rsp = do_search(**params)
    if not rsp['ok']:
        flask.abort(404)

    woeid = int(rsp['rows'][0]['woe:id'])
    loc = flask.url_for('place_page', woeid=woeid)
    return flask.redirect(loc, code=303)


@app.route('/search/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def search_page():
    """
    Search page handler
    """

    q = get_str('q')
    q = get_single(q)

    if q:
        if re.match(r'^\d+$', q):
            woeid = int(q)
            _query, doc = get_by_id(woeid)

            if doc:
                loc = flask.url_for('place_page', woeid=woeid)
                return flask.redirect(loc, code=303)

        params = {
            'search': {
                'names_all': q
            },
            'exclude': {
                'placetypes': [0],
                'nullisland': True,
                'deprecated': True
            },
            'facets': {
                'placetypes': True,
                'countries': False
            }
        }
        placetype_name = get_str('placetype')
        placetype_name = get_single(placetype_name)
        if placetype_name:
            _query, placetype = get_pt_by_name(placetype_name)
            if placetype:
                params['include'] = {
                    'placetypes': [int(placetype['id'])]
                }

        query, _params, rsp = do_search(**params)
        if rsp['ok']:
            if rsp['pagination']['total'] > 0 and rsp['pagination']['count'] > 0:
                sidebar_woeid = int(rsp['rows'][0]['woe:id'])
                args = {
                    'name': True
                }
                rows = inflatify(rsp['rows'], **args)
                sidebar_name = rows[0]['inflated']['name']
                doc = rows[0]

            else:
                rows = []
                params = {
                    'size': 1,
                    'random': True,
                    'include': {
                        'centroid': True
                    },
                    'exclude': {
                        'placetypes': [0,
                                       11,
                                       25],
                        'nullisland': True,
                        'deprecated': True
                    }
                }

                _query, _params, res = do_search(**params)
                if res['ok']:
                    args = {
                        'name': True
                    }
                    sidebar_woeid = int(res['rows'][0]['woe:id'])
                    rows = inflatify(res['rows'], **args)
                    sidebar_name = rows[0]['inflated']['name']
                    doc = rows[0]
                    rows = []

            template_args = {
                'map': True,
                'title': f'Search results for "{q}"',
                'query': q,
                'results': rows,
                'woeid': sidebar_woeid,
                'name': sidebar_name,
                'doc': doc,
                'pagination': build_pagination_urls(pagination=rsp['pagination']),
                'facets': rsp['facets'] if 'facets' in rsp else [],
                'es_query': trim_query(query),
                'took': rsp['took_sec']
            }
            template_args = get_geometry(doc, template_args)
            return flask.render_template('results.html.jinja', **template_args)

    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0,
                           11,
                           25],
            'nullisland': True,
            'deprecated': True
        }
    }

    _query, _params, rsp = do_search(**params)
    if rsp['ok']:
        args = {
            'name': True
        }
        sidebar_woeid = int(rsp['rows'][0]['woe:id'])
        rows = inflatify(rsp['rows'], **args)
        sidebar_name = rows[0]['inflated']['name']

        template_args = {
            'map': True,
            'title': 'Search',
            'woeid': sidebar_woeid,
            'name': sidebar_name,
            'doc': rows[0]
        }
        template_args = get_geometry(rows[0], template_args)
        return flask.render_template('search.html.jinja', **template_args)

    return {}, None


def get_by_id(woeid, **kwargs):
    """
    Get a document by WOEID
    """

    includes = kwargs.get('includes', [])
    excludes = kwargs.get('excludes', [])

    query = {
        'ids': {
            'values': [woeid]
        }
    }
    body = {
        'query': query
    }

    if includes or excludes:
        body['_source'] = {}
        if includes:
            body['_source']['includes'] = includes
        if excludes:
            body['_source']['excludes'] = excludes

    rsp = flask.g.docmgr.query(body=body)

    if 'hits' in rsp:
        return body, flask.g.docmgr.single(rsp)

    if 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return {}, None


def get_by_ids(*, ids, **kwargs):
    """
    Get documents by multiple WOEIDs
    """

    includes = kwargs.get('includes', [])
    excludes = kwargs.get('excludes', [])

    query = {
        'ids': {
            'values': ids
        }
    }
    body = {
        'query': query
    }

    if includes or excludes:
        body['_source'] = {}
        if includes:
            body['_source']['includes'] = includes
        if excludes:
            body['_source']['excludes'] = excludes

    rsp = flask.g.docmgr.query(body=body)

    if 'hits' in rsp:
        return flask.g.docmgr.rows(rsp)

    if 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return None


def get_pt_by_id(ptid, **kwargs):
    """
    Get a placetype by id
    """

    includes = kwargs.get('includes', [])
    excludes = kwargs.get('excludes', [])

    query = {
        'ids': {
            'values': [ptid]
        }
    }
    body = {
        'query': query
    }

    if includes or excludes:
        body['_source'] = {}
        if includes:
            body['_source']['includes'] = includes
        if excludes:
            body['_source']['excludes'] = excludes

    rsp = flask.g.ptmgr.query(body=body)

    if 'hits' in rsp:
        return body, flask.g.ptmgr.single(rsp)

    if 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return {}, None


def get_pt_by_name(name, **kwargs):
    """
    Get a placetype by name
    """

    includes = kwargs.get('includes', [])
    excludes = kwargs.get('excludes', [])

    body = {
        'query': {
            'bool': {
                'must': [{
                    'match': {
                        'shortname': name.lower()
                    }
                }]
            }
        }
    }

    body['_source'] = {}
    if includes:
        body['_source']['includes'] = includes
    if excludes:
        body['_source']['excludes'] = excludes

    rsp = flask.g.ptmgr.query(body=body)

    if 'hits' in rsp:
        return body, flask.g.ptmgr.single(rsp)

    if 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return {}, None


def get_language(code):
    """
    Get language by ISO-639 code
    """

    try:
        lang = iso639.languages.get(part2b=code.lower())
        return lang.name
    except KeyError as _exc:    # noqa: F841
        return 'Unknown'


def get_param(key, sanitize=None):
    """
    Get (and sanitise) a query parameter
    """

    param = flask.request.args.getlist(key)
    if len(param) == 0:
        return None

    if sanitize:
        param = list(map(sanitize, param))

    return param


def get_single(value):
    """
    Collapse a list to a single value
    """
    if value and isinstance(value, list):
        value = value[0]

    return value


def get_str(key):
    """
    Get (and sanitise) a string query parameter
    """

    param = get_param(key, sanitize_str)
    return param


def get_int(key):
    """
    Get (and sanitise) an integer query parameter
    """

    param = get_param(key, sanitize_int)
    return param


def get_float(key):
    """
    Get (and sanitise) a float query parameter
    """
    param = get_param(key, sanitize_float)
    return param


def sanitize_str(value):
    """
    Sanitise a string
    """

    if value:
        value = value.strip()

    return value


def sanitize_int(value):
    """
    Sanitise an integer
    """

    if value:
        value = int(value)

    return value


def sanitize_float(value):
    """
    Sanitise a float
    """

    if value:
        value = float(value)

    return value


def listify(params):
    """
    Convert a string or list of strings to a lowercased list
    """
    if not params:
        return []

    if not isinstance(params, list):
        params = [params]

    ret = []
    for param in params:
        ret.append(param.lower())

    return ret


def excludify():
    """
    Build query exclusions
    """

    includes = listify(get_str('include'))
    excludes = {
        'placetypes': [0],
        'nullisland': True,
        'deprecated': True
    }
    if 'unknown' in includes:
        excludes.pop('placetypes')
    if 'nullisland' in includes:
        excludes.pop('nullisland')
    if 'deprecated' in includes:
        excludes.pop('deprecated')

    return includes, excludes


def get_queryparams():
    """
    Get all supported query parameters
    """

    params = {
        'placetype': get_single(get_str('placetype')),
        'page': get_single(get_int('page')),
        'lat': get_single(get_float('lat')),
        'lng': get_single(get_float('lng')),
        'radius': get_single(get_float('radius')),
        'q': get_single(get_str('q')),
        'includes': listify(get_str('include')),
        'excludes': {
            'placetypes': [0],
            'nullisland': True,
            'deprecated': True
        },
        'view_args': flask.request.view_args
    }
    if 'unknown' in params['includes']:
        params['excludes'].pop('placetypes')
    if 'nullisland' in params['includes']:
        params['excludes'].pop('nullisland')
    if 'deprecated' in params['includes']:
        params['excludes'].pop('deprecated')

    return params


def do_search(**kwargs):
    """
    Search ... !
    """

    params = kwargs
    body = search_query(**params)

    randomify = kwargs.get('random', False)
    nearby = kwargs.get('nearby',
                        {})
    sort = []
    if nearby:
        sort = [
            {
                'woe:scale': {
                    'order': 'desc',
                    'mode': 'max'
                }
            },
            {
                'woe:id': {
                    'order': 'asc',
                    'mode': 'max'
                }
            }
        ]

    elif not randomify:
        sort = [
            {
                'woe:scale': {
                    'order': 'asc',
                    'mode': 'max'
                }
            },
            {
                'geom:area': {
                    'order': 'asc',
                    'mode': 'max'
                }
            },
            {
                'woe:id': {
                    'order': 'asc',
                    'mode': 'max'
                }
            }
        ]

    if sort:
        body['sort'] = sort

    params = {
        'after': True
    }
    token = get_str('token')
    token = get_single(token)

    page = get_int('page')
    page = get_single(page)

    if token:
        params['token'] = token
    elif page:
        params['page'] = page
    else:
        pass

    rsp = flask.g.docmgr.query(body=body, params=params)
    rsp = flask.g.docmgr.standard_rsp(rsp, **params)

    return body, params, rsp


def search_query(**kwargs):
    """
    Build the Elasticsearch search query
    """

    size = kwargs.get('size', 10)
    search = kwargs.get('search',
                        {})
    country = kwargs.get('iso', None)
    nearby = kwargs.get('nearby',
                        {})
    randomify = kwargs.get('random', False)
    source = kwargs.get('source', None)
    if not source:
        source = True

    query = {
        'bool': {
            'must': [],
            'must_not': []
        }
    }

    if search:
        names_all = search.get('names_all', None)
        names_alt = search.get('names_alt', None)
        names_colloquial = search.get('names_colloquial', None)
        names_preferred = search.get('names_preferred', None)
        names_variant = search.get('names_variant', None)
        search_field = None
        search_value = None

        if names_all:
            search_field = 'names_all'
            search_value = names_all
        elif names_alt:
            search_field = 'names_alt'
            search_value = names_alt
        elif names_colloquial:
            search_field = 'names_colloquial'
            search_value = names_colloquial
        elif names_preferred:
            search_field = 'names_preferred'
            search_value = names_preferred
        elif names_variant:
            search_field = 'names_variant'
            search_value = names_variant

        if search_field and search_value:
            query['bool']['must'].append({'match': {
                search_field: search_value
            }})

    elif country:
        query['bool']['must'].append({'match': {
            'iso:country': country.upper()
        }})

    elif nearby:
        query['bool']['must'].append(
            {
                'geo_shape': {
                    'geometry': {
                        'shape': {
                            'type': 'circle',
                            'radius': nearby['radius'],
                            'coordinates': nearby['coordinates']
                        }
                    }
                }
            }
        )

    query = enfilter(query, **kwargs)
    body = {
        'size': size,
        'track_total_hits': True,
        '_source': source
    }

    if randomify:
        rightnow = int(time.time())
        seed = random.randint(0, rightnow)
        body['query'] = {
            'function_score': {
                'query': query,
                'functions': [{
                    'random_score': {
                        'seed': seed,
                        'field': 'woe:id'
                    }
                }],
                'score_mode': 'sum',
                'boost_mode': 'sum'
            }
        }

    elif query:
        if query['bool']['must'] or query['bool']['must_not']:
            body['query'] = query

    facets = enfacet(**kwargs)
    if facets:
        body['aggs'] = facets

    return body


def enfilter(query, **kwargs):
    """
    Add filters to the search query
    """

    includes = kwargs.get('include',
                          {})
    excludes = kwargs.get('exclude',
                          {})

    must = []
    mustnot = []

    if includes:
        centroid = includes.get('centroid', False)
        nullisland = includes.get('nullisland', False)

        if centroid:
            must.append({'exists': {
                'field': 'woe:latitude'
            }})
            must.append({'exists': {
                'field': 'woe:longitude'
            }})

        if nullisland:
            must.append({'term': {
                'geom:latitude': {
                    'value': 0.0
                }
            }})
            must.append({'term': {
                'geom:longitude': {
                    'value': 0.0
                }
            }})
            mustnot.append({'term': {
                'woe:id': {
                    'value': 1
                }
            }})
            mustnot.append({'exists': {
                'field': 'woe:superseded_by'
            }})

        placetypes = includes.get('placetypes', [])
        if placetypes:
            ids = []
            for place_type in placetypes:
                _query, placetype = get_pt_by_id(place_type)
                if not placetype:
                    flask.current_app.logger.warning(
                        'Invalid enfilter:include:placetype %s',
                        place_type
                    )
                    flask.abort(404)

                ids.append(place_type)

            if len(ids) == 1:
                must.append({'term': {
                    'woe:placetype': ids[0]
                }})
            else:
                must.append({'terms': {
                    'woe:placetype': ids
                }})

    if excludes:
        placetypes = excludes.get('placetypes', [])
        nullisland = excludes.get('nullisland', False)
        deprecated = excludes.get('deprecated', False)

        if placetypes:
            ids = []
            for place_type in placetypes:
                _query, placetype = get_pt_by_id(place_type)
                if not placetype:
                    flask.current_app.logger.warning(
                        'Invalid enfilter:exclude:placetype %s',
                        place_type
                    )
                    flask.abort(404)

                ids.append(place_type)

            if len(ids) == 1:
                mustnot.append({'term': {
                    'woe:placetype': ids[0]
                }})
            else:
                mustnot.append({'terms': {
                    'woe:placetype': ids
                }})

        if nullisland:
            mustnot.append({'term': {
                'geom:latitude': {
                    'value': 0.0
                }
            }})
            mustnot.append({'term': {
                'geom:longitude': {
                    'value': 0.0
                }
            }})

        if deprecated:
            mustnot.append({'exists': {
                'field': 'woe:superseded_by'
            }})

    if must:
        query['bool']['must'].extend(must)
    if mustnot:
        query['bool']['must_not'].extend(mustnot)

    return query


def enfacet(**kwargs):
    """
    Add facets to the search query
    """

    facets = {}
    facets_param = kwargs.get('facets',
                              {})
    if facets_param:
        placetypes = facets_param.get('placetypes', False)
        countries = facets_param.get('countries', False)

        if placetypes:
            facets['placetypes'] = {
                'terms': {
                    'field': 'woe:placetype_name',
                    'size': 10000
                }
            }
        if countries:
            facets['countries'] = {
                'terms': {
                    'field': 'iso:country',
                    'size': 10000
                }
            }

    return facets


def inflatify(docs, **kwargs):
    """
    Inflate a WoePlanet document by expanding WOEIDs to their details
    """

    inflate_name = kwargs.get('name', True)
    inflate_hierarchy = kwargs.get('hierarchy', False)
    inflate_adjacencies = kwargs.get('adjacencies', False)
    inflate_aliases = kwargs.get('aliases', False)
    inflate_children = kwargs.get('children', False)
    single = False
    name = None
    hierarchy = {}
    adjacencies = []
    aliases = []
    children = {}

    if isinstance(docs, dict):
        single = True
        docs = [docs]

    for idx, doc in enumerate(docs):
        if inflate_name and 'woe:name' in doc:
            name = doc.get('woe:name', None)
            inflate_hierarchy = True

        if inflate_hierarchy:
            hierarchy = {}
            try:
                source = doc.get('woe:hierarchy',
                                 {})
                if source:
                    args = {
                        'includes': ['woe:id',
                                     'woe:name']
                    }
                    for placetype_name, woeid in source.items():
                        if woeid != 0:
                            _query, hdoc = get_by_id(woeid, **args)
                            if doc:
                                hierarchy[placetype_name] = hdoc

            except Exception as exc:
                flask.current_app.logger.error(
                    'Caught exception in inflatify:hierarchy for woe:id %s',
                    doc['woe:id']
                )
                raise RuntimeError(exc) from exc

        if inflate_name and name:
            labels = [name]
            if 'county' in hierarchy:
                labels.append(hierarchy['county']['woe:name'])
            if 'state' in hierarchy:
                labels.append(hierarchy['state']['woe:name'])
            if 'country' in hierarchy:
                labels.append(hierarchy['country']['woe:name'])

            name = ', '.join(labels)

        if inflate_adjacencies:
            source = doc.get('woe:adjacent', [])
            if source:
                args = {
                    'includes': ['woe:id',
                                 'woe:placetype_name',
                                 'woe:name']
                }
                adjs = {}
                for woeid in source:
                    _query, adoc = get_by_id(woeid, **args)
                    if doc:
                        pts = flask.g.inflect.plural(adoc['woe:placetype_name'])
                        if pts not in adjs:
                            adjs[pts] = [adoc]
                        else:
                            adjs[pts].append(adoc)

                for placetype_name in adjs:
                    adjs[placetype_name] = sorted(adjs[placetype_name], key=lambda k: k['woe:name'])

                adjacencies = dict(collections.OrderedDict(sorted(adjs.items())))

        if inflate_aliases:
            for prop in doc:
                match = re.fullmatch(r'^woe:alias_([A-Z]{3})_[A-Z]{1}$', prop)
                if match:
                    code = match.group(1)
                    if code == 'UNK':
                        language = 'Unknown'

                    else:
                        lang = iso639.languages.get(part2b=code.lower())
                        language = lang.name

                    aliases.append({
                        'lang': language,
                        'aliases': doc.get(prop)
                    })

            aliases = sorted(aliases, key=lambda k: k['lang'])

        if inflate_children:
            source = doc.get('woe:children',
                             {})
            if source:
                args = {
                    'includes': ['woe:id',
                                 'woe:name']
                }
                for placetype_name, ids in source.items():
                    _query, placetype_name = get_pt_by_name(placetype_name)
                    sdocs = get_by_ids(ids=ids, **args)
                    if sdocs:
                        pts = flask.g.inflect.plural(placetype_name['name'])
                        children[pts] = sorted(sdocs, key=lambda k: k['woe:name'])

                children = dict(collections.OrderedDict(sorted(children.items())))

        docs[idx]['inflated'] = {
            'name': name,
            'hierarchy': hierarchy,
            'adjacencies': adjacencies,
            'aliases': aliases,
            'children': children
        }

    return docs[0] if single else docs


def build_pagination_urls(*, pagination):
    """
    Build previous/next pagination URLs
    """
    prev_url = None
    next_url = None

    pages = int(pagination['pages'])
    page = int(pagination['page'])

    if pages > 1:
        if page == 1:
            pass
        else:
            prev_url = rebuild_url(page=page - 1)

        if page == pages:
            pass
        else:
            next_url = rebuild_url(page=page + 1)

    pagination['urls'] = {
        'prev': prev_url,
        'next': next_url
    }

    return pagination


def rebuild_url(*, page):
    """
    Rebuild a URL
    """
    querystring = flask.request.query_string.decode()
    querystring = dict(urllib.parse.parse_qsl(querystring))

    if querystring.get('page', False):
        querystring.pop('page')

    querystring['page'] = page

    return f'{flask.request.path}?{urllib.parse.urlencode(querystring)}'


def make_source_urls(doc):
    """
    Generate the source, repo and GeoJSON URLs for a WOEID
    """

    if 'woe:repo' not in doc:
        raise RuntimeError(f"Missing woe:repo for {doc['woe:id']}")

    repo_url = f"https://github.com/woeplanet-data/{doc['woe:repo']}"
    file_path = uri.id2abspath('/', doc['woe:id'])
    geojson_url = uri.id2abspath((f'{repo_url}/blob/master/data'), doc['woe:id'])

    return {
        'source': file_path,
        'repo': repo_url,
        'geojson': geojson_url
    }


def trim_query(query):
    """
    Transform/trim an Elasticsearch JSON query to a string
    """

    if 'size' in query:
        query.pop('size')
    if 'track_total_hits' in query:
        query.pop('track_total_hits')
    if '_source' in query:
        query.pop('_source')

    return json.dumps(query, indent=2)


def docs_to_geojson(docs, terse=True):
    """
    Transforms multiple WoePlanet Elasticsearch documents to GeoJSON
    """

    res = []
    for doc in docs:
        res.append(doc_to_geojson(doc, terse))

    return res


def doc_to_geojson(doc, terse=True):
    """
    Transform a WoePlanet Elasticsearch document to GeoJSON
    """

    if not doc:
        return None

    props = doc
    woeid = props['woe:id']
    geom = props.pop('geometry',
                     {})
    bbox = props.pop('geom:bbox', [])
    lat = props.pop('geom:latitude', 0.0)
    lon = props.pop('geom:longitude', 0.0)

    if not geom:
        geom = {
            'type': 'Point',
            'coordinates': [lon,
                            lat]
        }

    geojson = {
        'type': 'Feature',
        'id': woeid,
        'properties': props,
        'bbox': bbox,
        'geometry': geom
    }
    if terse:
        geojson['properties'] = {}

    return geojson


def get_geometry(doc, args):
    """
    Extract the geometry from a WoePlanet Elasticsearch document
    """
    bbox = doc.get('geom:bbox', [])
    if not bbox:
        bbox = doc.get('woe:bbox', [])

    if bbox:
        args['bounds'] = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]

    point = doc.get('geom:centroid', [])
    if not point:
        point = doc.get('woe:centroid', [])
        if not point:
            point = [doc.get('geom:longitude', 0.0), doc.get('geom:latitude', 0.0)]

    if point and point[0] != 0.0 and point[1] != 0.0:
        args['centroid'] = [point[1], point[0]]

    return args
