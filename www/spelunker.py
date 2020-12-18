#!/usr/bin/env python

# FLASK_ENV=development FLASK_APP=spelunker.py flask run --host=babbage.home.vicchi.org --port=5001
# gunicorn --pid run/woeplanet.pid --workers 3 --bind unix:run/woeplanet.sock --reload --reload-extra-file querymanager.py  --reload-extra-file static/css/site.css --reload-extra-file static/js/site.js woeplanet-spelunker:app

import collections
import dotenv
import flask
import flask_caching
import inflect
import iso639
import json
import os
import random
import re
import time
import urllib

import querymanager

import woeplanet.utils.uri as uri

dotenv.load_dotenv(dotenv.find_dotenv())

app = flask.Flask(__name__)
cache = flask_caching.Cache(
    config={
        'CACHE_TYPE': 'filesystem',
        'CACHE_DEFAULT_TIMEOUT': 5,
        'CACHE_IGNORE_ERRORS': False,
        'CACHE_DIR': os.environ.get('WOE_CACHE_DIR'),
        'CACHE_THRESHOLD': 500,
        'CACHE_OPTIONS': {
            'mode': int(os.environ.get('WOE_CACHE_MASK'))
        }
    })
cache.init_app(app)

@app.template_filter()
def commafy(value):
    return '{:,}'.format(value)

@app.template_filter()
def anyfy(value):
    return flask.g.inflect.an(value)

@app.template_filter()
def pluralise(value, count):
    return flask.g.inflect.plural(value, count)

@app.errorhandler(404)
def page_not_found(error):
    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0, 11, 25],
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
            'title': '404 Hic Sunt Dracones',
            'woeid': sidebar_woeid,
            'name': sidebar_name,
            'doc': rows[0]
        }
        template_args = get_geometry(rows[0], template_args)
        return flask.render_template('404.html.jinja', **template_args), 404

@app.errorhandler(500)
@app.errorhandler(503)
def internal_server_error(error):
    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0, 11, 25],
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
            'title': '%s %s' % (error.code, error.name),
            'error': error,
            'woeid': sidebar_woeid,
            'name': sidebar_name,
            'doc': rows[0]
        }
        template_args = get_geometry(rows[0], template_args)
        return flask.render_template('500.html.jinja', **template_args), error.code

@app.before_request
def init():
    es_host = os.environ.get('WOE_ES_HOST', 'localhost')
    es_port = os.environ.get('WOE_ES_PORT', '9200')
    es_docidx = os.environ.get('WOE_ES_DOC_INDEX', 'woeplanet')
    es_ptidx = os.environ.get('WOE_ES_PT_INDEX', 'placetypes')

    flask.g.docidx = es_docidx
    flask.g.ptidx = es_ptidx
    flask.g.inflect = inflect.engine()
    flask.g.inflect.defnoun('miscellaneous', 'miscellaneous')
    flask.g.inflect.defnoun('county', 'counties')
    flask.g.docmgr = querymanager.QueryManager(host=es_host, port=es_port, index=es_docidx)
    flask.g.ptmgr = querymanager.QueryManager(host=es_host, port=es_port, index=es_ptidx)
    flask.g.nearby_radius = '1km'
    flask.g.queryparams = get_queryparams()

@app.route('/', methods=['GET'])
@cache.cached(timeout=60)
def home():
    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0, 11, 25],
            'nullisland': True,
            'deprecated': True
        }
    }

    _query, _params, rsp = do_search(**params)

    if rsp['ok']:
        id = int(rsp['rows'][0]['woe:id'])
        args = {
            'name': True
        }
        rows = inflatify(rsp['rows'], **args)
        doc = rows[0]
        template_args = {
            'map': True,
            'title': 'Home',
            'woeid': id,
            'name': doc['inflated']['name'],
            'doc': doc
        }
        template_args = get_geometry(doc, template_args)
        return flask.render_template('home.html.jinja', **template_args)

    else:
        flask.abort(404)


@app.route('/about/', methods=['GET'])
def about():
    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0, 11, 25],
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
            'iso': doc.get('iso:country', 'GB'),
            'nearby': doc['woe:id'],
            'name': name,
            'doc': doc
        }
        template_args = get_geometry(doc, template_args)
        return flask.render_template('about.html.jinja', **template_args)

    else:
        flask.abort(404)

@app.route('/credits/', methods=['GET'])
@cache.cached(timeout=60)
def credits():
    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0, 11, 25],
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

    else:
        flask.abort(404)

@app.route('/countries/', methods=['GET'])
@cache.cached(timeout=60)
def countries():
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
                    'placetypes': [ 12 ]
                },
                'exclude': excludes,
                # 'exclude': {
                #     'placetypes': [ 0 ],
                #     'deprecated': True
                # },
                'source': {
                    'includes': [
                        'woe:name',
                        'iso:country'
                    ]
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
                'placetypes': [0, 11, 25],
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

    flask.abort(404)

@app.route('/country/<string:iso>/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def country(iso):
    iso = iso.upper()
    params = {
        'iso': iso,
        'exclude': {
            'placetype': [0, 12],
            'nullisland': True,
            'deprecated': True
        },
        'facets': {
            'placetypes': True
        }
    }
    placetype = get_str('placetype')
    placetype = get_single(placetype)
    if placetype:
        _query, pt = get_pt_by_name(placetype)
        if pt:
            params['include'] = {
                'placetypes': [ int(pt['id']) ]
            }

    _query, _params, rsp = do_search(**params)
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
                    'placetypes': [0, 11, 25],
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
            'title': 'Child places for %s' % iso,
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

@app.route('/id/<int:id>/', methods=['GET'])
@cache.cached(timeout=60)
def info(id):
    _query, doc = get_by_id(id)
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
        'title': 'WOEID %s (%s)' % (doc['woe:id'], doc['woe:name'] if 'woe:name' in doc else 'Unknown'),
        'lang': get_language(doc['woe:lang']) if 'woe:lang' in doc else 'Unknown',
        'name': doc['woe:name'] if 'woe:name' in doc else 'Unknown',
        'placetype': placetype,
        'doc': doc,
        'urls': make_source_urls(doc)
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('place.html.jinja', **template_args)

@app.route('/id/<int:id>/map/', methods=['GET'])
@cache.cached(timeout=60)
def map_id(id):
    _query, doc = get_by_id(id)
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

    popup = '<h2>This is <a href="%s">%s</a></h2>' % (flask.url_for('info', id=id), doc['woe:name'])

    template_args = {
        'map': True,
        'title': 'WOEID %s (%s) | Map' % (doc['woe:id'], doc['woe:name'] if 'woe:name' in doc else 'Unknown'),
        'name': doc['woe:name'] if 'woe:name' in doc else 'Unknown',
        'woeid': id,
        'placetype': placetype,
        'doc': doc,
        'popup': popup,
    }
    template_args = get_geometry(doc, template_args)
    return flask.render_template('map.html.jinja', **template_args)


@app.route('/id/<int:id>/nearby/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def nearby_id(id):
    _query, doc = get_by_id(id)
    if not doc:
        flask.abort(404)

    args = {
        'name': True
    }
    doc = inflatify(doc, **args)
    nearby_name = doc['inflated']['name']
    nearby_id = id

    radius = get_float('radius')
    radius = get_single(radius)
    if not radius:
        radius = flask.g.nearby_radius

    coords = [0,0]
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
            'placetypes': [0, 11, 25],
            'nullisland': True,
            'deprecated': True
        },
        'facets': {
            'placetypes': True,
            'countries': False
        }
    }

    placetype = get_str('placetype')
    placetype = get_single(placetype)
    if placetype:
        _query, pt = get_pt_by_name(placetype)
        if pt:
            params['include'] = {
                'placetypes': [ int(pt['id']) ]
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
                    'placetypes': [0, 11, 25],
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
            'title': 'Places near %s' % sidebar_name,
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
def nearby():
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
                'placetypes': [0, 11, 25],
                'nullisland': True,
                'deprecated': True
            },
            'facets': {
                'placetypes': True,
                'countries': False
            }
        }

        placetype = get_str('placetype')
        placetype = get_single(placetype)
        if placetype:
            _query, pt = get_pt_by_name(placetype)
            if pt:
                params['include'] = {
                    'placetypes': [int(pt['id'])]
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
                        'placetypes': [0, 11, 25],
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

    params = {
        'size': 1,
        'random': True,
        'include': {
            'centroid': True
        },
        'exclude': {
            'placetypes': [0, 11, 25],
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
        'nearby_id': nearby_id,
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
def nullisland():
    params = {
        'include': {
            'nullisland': True
        },
        'facets': {
            'placetypes': True
        }
    }
    placetype = get_str('placetype')
    placetype = get_single(placetype)
    if placetype:
        _query, pt = get_pt_by_name(placetype)
        if pt:
            params['include']['placetypes'] = [ int(pt['id']) ]

    query, _params, rsp = do_search(**params)
    if rsp['ok']:
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
def placetypes():
    includes, excludes = excludify()
    params = {
        'size': 0,
        'exclude': excludes,
        'facets': {
            'placetypes': True
        }
    }
    query, _params, rsp = do_search(**params)
    if rsp['ok']:
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
                'placetypes': [0, 11, 25],
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

    flask.abort(404)

@app.route('/placetype/<string:placetype>/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def placetype(placetype):
    _query, pt = get_pt_by_name(placetype)
    if pt:
        ptid = pt['id']
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
        if rsp['ok']:
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
                'title': 'Search results for placetype "%s"' % placetype,
                'results': rows,
                'woeid': sidebar_woeid,
                'name': sidebar_name,
                'doc': doc,
                'placetype': pt,
                'pagination': build_pagination_urls(pagination=rsp['pagination']),
                'facets': rsp['facets'] if 'facets' in rsp else [],
                'includes': includes if includes else None,
                'es_query': trim_query(query)
            }
            template_args = get_geometry(doc, template_args)
            return flask.render_template('results.html.jinja', **template_args)

    flask.abort(404)

@app.route('/random/', methods=['GET'])
@cache.cached(timeout=60)
def random_id():
    params = {
        'size': 1,
        'random': True,
        'search': {},
        'include': {},
        'exclude': {
            'placetypes': [0, 11, 25],
            'nullisland': True,
            'deprecated': True
        },
        'facets': {
            'placetypes': False,
            'countries': False
        }
    }
    _query, _params, rsp = do_search(**params)
    if rsp['ok']:
        id = int(rsp['rows'][0]['woe:id'])
        loc = flask.url_for('info', id=id)
        return flask.redirect(loc, code=303)

    else:
        flask.abort(404)

@app.route('/search/', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def search():
    q = get_str('q')
    q = get_single(q)

    if q:
        if re.match(r'^\d+$', q):
            id = int(q)
            _query, doc = get_by_id(id)

            if doc:
                loc = flask.url_for('info', id=id)
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
        placetype = get_str('placetype')
        placetype = get_single(placetype)
        if placetype:
            _query, pt = get_pt_by_name(placetype)
            if pt:
                params['include'] = {
                    'placetypes': [ int(pt['id']) ]
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
                        'placetypes': [0, 11, 25],
                        'nullisland': True,
                        'deprecated': True
                    }
                }

                _query, _params, res = do_search(**params)
                if res['ok']:
                    args = {'name': True}
                    sidebar_woeid = int(res['rows'][0]['woe:id'])
                    rows = inflatify(res['rows'], **args)
                    sidebar_name = rows[0]['inflated']['name']
                    doc = rows[0]
                    rows = []

            template_args = {
                'map': True,
                'title': 'Search results for "%s"' % q,
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
            'placetypes': [0, 11, 25],
            'nullisland': True,
            'deprecated': True
        }
    }

    _query, _params, rsp = do_search(**params)
    if rsp['ok']:
        args = {'name': True}
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


def get_by_id(id, **kwargs):
    includes = kwargs.get('includes', [])
    excludes = kwargs.get('excludes', [])

    query = {'ids': {'values': [id]}}
    body = {'query': query}

    if includes or excludes:
        body['_source'] = {}
        if includes:
            body['_source']['includes'] = includes
        if excludes:
            body['_source']['excludes'] = excludes

    rsp = flask.g.docmgr.query(body=body)

    if 'hits' in rsp:
        return body, flask.g.docmgr.single(rsp)

    elif 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return {}, None

def get_by_ids(*, ids, **kwargs):
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

    elif 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return None

def get_pt_by_id(id, **kwargs):
    includes = kwargs.get('includes', [])
    excludes = kwargs.get('excludes', [])

    query = {
        'ids': {
            'values': [ id ]
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

    elif 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return {}, None

def get_pt_by_name(name, **kwargs):
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

    elif 'error' in rsp:
        flask.current_app.logger.error(rsp['error'])

    else:
        flask.current_app.logger.error(rsp)

    return {}, None

def get_language(code):
    try:
        lang = iso639.languages.get(part2b=code.lower())
        return lang.name
    except KeyError as _:
        return 'Unknown'

def get_param(key, sanitize=None):
    param = flask.request.args.getlist(key)
    if len(param) == 0:
        return None

    if sanitize:
        param = list(map(sanitize, param))

    return param

def get_single(value):
    if value and isinstance(value, list):
        value = value[0]

    return value

def get_str(key):
    param = get_param(key, sanitize_str)
    return param

def get_int(key):
    param = get_param(key, sanitize_int)
    return param

def get_float(key):
    param = get_param(key, sanitize_float)
    return param

def sanitize_str(str):
    if str:
        str = str.strip()

    return str

def sanitize_int(i):
    if i:
        i = int(i)

    return i

def sanitize_float(f):
    if f:
        f = float(f)

    return f

def listify(param):
    if not param:
        return []

    if not isinstance(param, list):
        param = [param]

    ret = []
    for p in param:
        ret.append(p.lower())

    return ret

def excludify():
    includes = listify(get_str('include'))
    excludes = {
        'placetypes': [ 0 ],
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
    params = {
        'placetype': get_single(get_str('placetype')),
        'page': get_single(get_int('page')),
        'lat': get_single(get_float('lat')),
        'lng': get_single(get_float('lng')),
        'radius': get_single(get_float('radius')),
        'q': get_single(get_str('q')),
        'includes': listify(get_str('include')),
        'excludes': {
            'placetypes': [ 0 ],
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
    params = kwargs
    body = search_query(**params)

    randomify = kwargs.get('random', False)
    nearby = kwargs.get('nearby', {})
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
    size = kwargs.get('size', 10)
    search = kwargs.get('search', {})
    country = kwargs.get('iso', None)
    nearby = kwargs.get('nearby', {})
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
            query['bool']['must'].append({
                'match': {
                    search_field: search_value
                }
            })

    elif country:
        query['bool']['must'].append({
            'match': {
                'iso:country': country.upper()
            }
        })

    elif nearby:
        query['bool']['must'].append({
            'geo_shape': {
                'geometry': {
                    'shape': {
                        'type': 'circle',
                        'radius': nearby['radius'],
                        'coordinates': nearby['coordinates']
                    }
                }
            }
        })

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
                'functions': [
                    {
                        'random_score': {
                            'seed': seed,
                            'field': 'woe:id'
                        }
                    }
                ],
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
    includes = kwargs.get('include', {})
    excludes = kwargs.get('exclude', {})

    must = []
    mustnot = []

    if includes:
        centroid = includes.get('centroid', False)
        nullisland = includes.get('nullisland', False)

        if centroid:
            must.append({
                'exists': {
                    'field': 'woe:latitude'
                }
            })
            must.append({
                'exists': {
                    'field': 'woe:longitude'
                }
            })

        if nullisland:
            must.append({
                'term': {
                    'geom:latitude': {
                        'value': 0.0
                    }
                }
            })
            must.append({
                'term': {
                    'geom:longitude': {
                        'value': 0.0
                    }
                }
            })
            mustnot.append({
                'term': {
                    'woe:id': {
                        'value': 1
                    }
                }
            })
            mustnot.append({
                'exists': {
                    'field': 'woe:superseded_by'
                }
            })

        placetypes = includes.get('placetypes', [])
        if placetypes:
            ids = []
            for p in placetypes:
                _query, pt = get_pt_by_id(p)
                if not pt:
                    flask.current_app.logger.warning('Invalid enfilter:include:placetype %s' % p)
                    flask.abort(404)

                ids.append(p)

            if len(ids) == 1:
                must.append({
                    'term': {
                        'woe:placetype': ids[0]
                    }
                })
            else:
                must.append({
                    'terms': {
                        'woe:placetype': ids
                    }
                })

    if excludes:
        placetypes = excludes.get('placetypes', [])
        nullisland = excludes.get('nullisland', False)
        deprecated = excludes.get('deprecated', False)

        if placetypes:
            ids = []
            for p in placetypes:
                _query, pt = get_pt_by_id(p)
                if not pt:
                    flask.current_app.logger.warning('Invalid enfilter:exclude:placetype %s' % p)
                    flask.abort(404)

                ids.append(p)

            if len(ids) == 1:
                mustnot.append({
                    'term': {
                        'woe:placetype': ids[0]
                    }
                })
            else:
                mustnot.append({
                    'terms': {
                        'woe:placetype': ids
                    }
                })

        if nullisland:
            mustnot.append({
                'term': {
                    'geom:latitude': {
                        'value': 0.0
                    }
                }
            })
            mustnot.append({
                'term': {
                    'geom:longitude': {
                        'value': 0.0
                    }
                }
            })

        if deprecated:
            mustnot.append({
                'exists': {
                    'field': 'woe:superseded_by'
                }
            })

    if must:
        query['bool']['must'].extend(must)
    if mustnot:
        query['bool']['must_not'].extend(mustnot)

    return query


def enfacet(**kwargs):
    facets = {}
    facets_param = kwargs.get('facets', {})
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
                source = doc.get('woe:hierarchy', {})
                if source:
                    args = {
                        'includes': ['woe:id', 'woe:name']
                    }
                    for placetype,id in source.items():
                        if id != 0:
                            _query, hdoc = get_by_id(id, **args)
                            if doc:
                                hierarchy[placetype] = hdoc

            except Exception as e:
                flask.current_app.logger.error('Caught exception in inflatify:hierarchy for woe:id %s' % doc['woe:id'])
                raise Exception(e)

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
                    'includes': ['woe:id', 'woe:placetype_name', 'woe:name']
                }
                adjs = {}
                for id in source:
                    _query, adoc = get_by_id(id, **args)
                    if doc:
                        pts = flask.g.inflect.plural(adoc['woe:placetype_name'])
                        if not pts in adjs:
                            adjs[pts] = [ adoc ]
                        else:
                            adjs[pts].append(adoc)

                for pt in adjs.keys():
                    adjs[pt] = sorted(adjs[pt], key=lambda k: k['woe:name'])

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
            source = doc.get('woe:children', {})
            if source:
                args = {
                    'includes': ['woe:id', 'woe:name']
                }
                for pt,ids in source.items():
                    _query, placetype = get_pt_by_name(pt)
                    sdocs = get_by_ids(ids=ids, **args)
                    if sdocs:
                        pts = flask.g.inflect.plural(placetype['name'])
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
    prev = None
    next = None

    pages = int(pagination['pages'])
    page = int(pagination['page'])

    if pages > 1:
        if page == 1:
            pass
        else:
            prev = rebuild_url(page=page - 1)

        if page == pages:
            pass
        else:
            next = rebuild_url(page=page+1)

    pagination['urls'] = {
        'prev': prev,
        'next': next
    }

    return pagination

def rebuild_url(*, page):
    qs = flask.request.query_string.decode()
    qs = dict(urllib.parse.parse_qsl(qs))

    if qs.get('page', False):
        qs.pop('page')

    qs['page'] = page

    return '%s?%s' % (flask.request.path, urllib.parse.urlencode(qs))

def make_source_urls(doc):
    if not 'woe:repo' in doc:
        raise Exception('Missing woe:repo for %s' % doc['woe:id'])

    repo_url = 'https://github.com/woeplanet-data/%s' % doc['woe:repo']
    file_path = uri.id2abspath('/', doc['woe:id'])
    geojson_url = uri.id2abspath(('%s/data' % repo_url), doc['woe:id'])

    return {
        'source': file_path,
        'repo': repo_url,
        'geojson': geojson_url
    }

def trim_query(query):
    if 'size' in query:
        query.pop('size')
    if 'track_total_hits' in query:
        query.pop('track_total_hits')
    if '_source' in query:
        query.pop('_source')

    return json.dumps(query, indent=2)

def docs_to_geojson(docs, terse=True):
    res = []
    for doc in docs:
        res.append(doc_to_geojson(doc, terse))

    return res

def doc_to_geojson(doc, terse=True):
    if not doc:
        return None

    props = doc
    woeid = props['woe:id']
    geom = props.pop('geometry', {})
    bbox = props.pop('geom:bbox', [])
    lat = props.pop('geom:latitude', 0.0)
    lon = props.pop('geom:longitude', 0.0)

    if not geom:
        geom = {
            'type': 'Point',
            'coordinates': [ lon, lat]
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
    bbox = doc.get('geom:bbox', [])
    if not bbox:
        bbox = doc.get('woe:bbox', [])

    if bbox:
        args['bounds'] = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]

    point = doc.get('geom:centroid', [])
    if not point:
        point = doc.get('woe:centroid', [])
        if not point:
            point  = [ doc.get('geom:longitude', 0.0), doc.get('geom:latitude', 0.0)]

    if point and point[0] != 0.0 and point[1] != 0.0:
        args['centroid'] = [point[1], point[0]]

    return args