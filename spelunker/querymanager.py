# pylint: disable=broad-exception-caught
"""
WoePlanet Elasticsearch connection and query wrangling
"""

import math

import flask
from elasticsearch import Elasticsearch, TransportError


class QueryManager:
    """
    WoePlanet Elasticsearch connection and query wrangler
    """

    def __init__(self, **kwargs):
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.index = kwargs.get('index')
        self.timeout = kwargs.get('timeout', 30)
        self.retries = kwargs.get('retries', 10)
        self.per_page = kwargs.get('per_page', 10)
        self.per_page_max = kwargs.get('per_page_max', 20)
        self.page = 1

        self.esclient = Elasticsearch(
            [f'{self.host}:{self.port}'],
            timeout=self.timeout,
            max_retries=self.retries,
            retry_on_timeout=True
        )

    def query(self, **kwargs):
        """
        Do the query thing ...
        """

        page = self.page
        per_page = self.per_page

        body = kwargs.get('body', {})
        params = kwargs.get('params', {})

        if params.get('per_page', None):
            per_page = params['per_page']
            per_page = min(per_page, self.per_page_max)

        if params.get('page', None):
            page = params['page']

        after = params.get('after', False)
        es_params = {}
        if after:
            if params.get('page', None):
                page = params['page']

                es_params = {
                    'from': (page - 1) * per_page,
                    'size': per_page
                }
                body['from'] = es_params['from']
                if 'size' not in body:
                    body['size'] = es_params['size']

        try:
            rsp = self.esclient.search(body=body, index=self.index)

        except TransportError as exc:
            flask.current_app.logger.error('ElasticSearch transport error: %s', exc)
            rsp = exc.info
        except Exception as exc:
            flask.current_app.logger.error('Other error: %s', exc)
            rsp = {
                'status': 500
            }
        else:
            rsp['status'] = 200

        # flask.current_app.logger.debug('rsp: %s', rsp)
        return rsp

    def single(self, rsp):
        """
        Return a single response document
        """

        count = len(rsp['hits']['hits'])
        if count == 0:
            return None

        if count > 1:
            flask.current_app.logger.warning('single called on a result set with %d results', count)
            return None

        return rsp['hits']['hits'][0]['_source']

    def first(self, rsp):
        """
        Return the first document
        """

        count = len(rsp['hits']['hits'])
        if count == 0:
            return None

        return rsp['hits']['hits'][0]['_source']

    def rows(self, rsp):
        """
        Return all documents
        """

        try:
            docs = []
            for doc in rsp['hits']['hits']:
                docs.append(doc['_source'])

            return docs
            # return rsp['hits']['hits']

        except Exception as _exc:    # noqa: F841
            return []

    def standard_rsp(self, rsp, **kwargs):
        """
        Format document(s) as a "standard" response
        """

        if rsp.get('status', None) == 404:
            error = 404
            try:
                error = rsp['error']['root_cause'][0]
            except Exception as _exc:    # noqa: F841
                flask.current_app.logger.warning(
                    'Unable to determine root cause for 404 error (%s)',
                    rsp['error']
                )

            return {
                'ok': False,
                'error': error,
                'took_ms': rsp['took'],
                'took_sec': rsp['took'] / 1000,
                'rows': [],
                'facets': [],
                'pagination': {
                    'total': 0,
                    'count': 0,
                    'per_page': 0,
                    'page': 0,
                    'pages': 0
                }
            }

        return {
            'ok': True,
            'took_ms': rsp['took'],
            'took_sec': rsp['took'] / 1000,
            'rows': self.rows(rsp),
            'facets': rsp['aggregations'] if 'aggregations' in rsp else [],
            'pagination': self.paginate(rsp, **kwargs)
        }

    def single_rsp(self, rsp, **kwargs):
        """
        Return a single "standard" document
        """

        if rsp.get('status', None) == 404:
            error = 404
            try:
                error = rsp['error']['root_cause'][0]
            except Exception as _exc:    # noqa: F841
                flask.current_app.logger.warning(
                    'Unable to determine root cause for 404 error (%s)',
                    rsp['error']
                )

            return {
                'ok': False,
                'error': error,
                'row': None,
                'pagination': {
                    'total': 0,
                    'count': 0,
                    'start': 0,
                    'per_page': 0,
                    'page': 0,
                    'pages': 0
                }
            }

        return {
            'ok': True,
            'row': self.single(rsp),
            'pagination': self.paginate(rsp,
                                        **kwargs)
        }

    def paginate(self, rsp, **kwargs):
        """
        Format pagination
        """

        per_page = kwargs.get('per_page', self.per_page)
        per_page = min(per_page, self.per_page_max)

        page = kwargs.get('page', self.page)
        hits = rsp['hits']
        total = hits['total']['value']
        docs = hits['hits']
        count = len(docs)

        pages = float(total) / float(per_page)
        pages = math.ceil(pages)
        pages = int(pages)

        pagination = {
            'total': total,
            'count': count,
            'start': per_page * (page - 1) + 1 if page > 1 else 1,
            'per_page': per_page,
            'page': page,
            'pages': pages
        }

        return pagination

    # def encode_token(self, *, token):
    #     token_json = json.dumps(token)
    #     token_jsonb = token_json.encode('utf-8')
    #     token_jsonb64 = base64.b64encode(token_jsonb)
    #     token_jsonb64s = token_jsonb64.decode('utf-8')
    #     return token_jsonb64s

    # def decode_token(self, *, token):
    #     token_strb = token.encode('utf-8')
    #     token_decoded = base64.b64decode(token_strb)
    #     token_decodeds = token_decoded.decode(token_decoded)
    #     token_json = json.loads(token_decodeds)
    #     return token_json
