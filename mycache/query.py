# -*-coding: utf-8-*-
# Author : Christopher Lee
# License: Apache License
# File   : model.py
# Date   : 2017-05-18 09-00
# Version: 0.0.1
# Description: description of this file.

import logging

from collections import defaultdict

from dataobj.manager import DataObjectsManager
# from mycache.factory import RedisCacheFactory
from mycache.utils import camel_to_underscore, get_query_fingerprint

logger = logging.getLogger(__name__)

__version__ = '0.0.1'
__author__ = 'Chris'


def query_cache(model):
    """
    ONLY WORKS ON A MODEL object

    Cache query results and track the changes to each model instance
    Delete related cache_key when a model instance is inserted, updated
    or deleted.
    """
    if model is None:
        return None

    if hasattr(model, 'objects') is False:
        raise TypeError('`{}` is not a `Model` class'.format(model))

    try:
        # Have we defined track conditions yet?
        model.Meta.cache_conditions
    except AttributeError:
        pass
    else:
        # change the model's data objects manager
        setattr(model, 'objects', DataObjectsManagerWithCache(model))

    return model


class DataObjectsManagerWithCache(DataObjectsManager):
    """
    Inherit from the `DataObjectsManager` so that we can
    track any modifications.
    """

    def __init__(self, model):
        super().__init__(model)
        self._dont_cache = False

    @property
    def cache_db(self):
        factory = getattr(self._model.Meta, 'cache_db_factory', None)
        if factory is None:
            raise RuntimeError("Cache db factory is not defined yet")

        assert callable(factory), 'Expected a callable factory, not {}'.format(factory)
        return factory()

    def update(self, model_instance):
        self._invalidate_related_cache(model_instance)
        return super().update(model_instance)

    def delete(self, model_instance):
        self._invalidate_related_cache(model_instance)
        return super().delete(model_instance)

    def dump(self, model_instance):
        self._invalidate_related_cache(model_instance)
        return super().dump(model_instance)

    def limit(self, how_many, offset=0):
        self._dont_cache = True
        return super().limit(how_many, offset)

    def order_by(self, *field_names, descending=False):
        self._dont_cache = True
        return super().order_by(*field_names, descending=descending)

    def all_cache(self):
        """
        Complex cache conditions are not supported now in this method.
        """
        # cache_db = RedisCacheFactory().make_redis_cache('data_objects')

        with CacheManager(self._model, self.cache_db) as cache:
            results = self.all()

            for key in self._get_valid_single_cache_keys():
                logger.debug('All cache with single condition key {}'.format(key))
                data = defaultdict(list)

                for item in results:
                    data[getattr(item, key)].append(item)

                for value, rows in data.items():
                    cache.add(self._get_single_query(key, value), *rows)

    def clear_cache(self):
        # cache_db = RedisCacheFactory().make_redis_cache('data_objects')
        with CacheManager(self._model, self.cache_db) as cache:
            cache.clear()

    def _get_single_query(self, key, value):
        return {'select': list(self._model.__mappings__.keys()),
                'where': {key: value},
                'limit': None,
                'order_by': None,
                'descending': False}

    def _get_valid_single_cache_keys(self):
        valid_cache_keys = []

        for key in getattr(self._model.Meta, 'cache_conditions', {}):
            if len(key.split('+')) != 1:
                continue

            if key in self._model:
                valid_cache_keys.append(key)

        return valid_cache_keys

    def _fetch_results(self):
        if self._dont_cache is True:
            super()._fetch_results()
            return

        if self._query_results_cache is not None:
            return self._query_results_cache

        # cache_db = RedisCacheFactory().make_redis_cache('data_objects')
        # Check Redis/File cache before accessing database
        with CacheManager(self._model, self.cache_db) as cache:
            results = cache.get(self._query_collector)

            if results is None:
                logger.warning(
                    'Load results from database for model "{}" with query condition "{}"'.format(self._model.__name__,
                                                                                                 self._query_collector[
                                                                                                     'where']))
                # Fetch results from database and save the results to cache
                super()._fetch_results()
                cache.add(self._query_collector, *list(self._query_results_cache))
            else:
                logger.info('Load results from cache for model "{}" with condition "{}"'.format(self._model.__name__,
                                                                                                self._query_collector[
                                                                                                    'where']))
                self._query_results_cache = results

    def _invalidate_related_cache(self, model_instance):
        # cache_db = RedisCacheFactory().make_redis_cache('data_objects')
        with CacheManager(self._model, self.cache_db) as cache:
            # Generate queries firstly
            queries = []
            for key in getattr(model_instance.Meta, 'cache_conditions', {}):
                possible_query = self._query_collector.copy()

                where = {}
                for condition in key.split('+'):
                    condition = condition.strip()
                    if condition == '*':
                        where = {}
                    else:
                        where[condition] = getattr(model_instance, condition, None)

                possible_query['where'] = where
                queries.append(possible_query)

            cache.remove(*queries)


class CacheManager(object):
    """
    Data cache manager
    """

    def __init__(self, model, cache_db):
        self._model = model
        self._cache_db = cache_db
        self._records = defaultdict(list)
        self._timeouts = dict()
        self._conditions = dict()
        try:
            # load track timeouts for each condition
            self._condition_timeout_map = {'&'.join(sorted(x.strip() for x in k.split('+'))): timeout for k, timeout in
                                           self._model.Meta.cache_conditions.items()}
        except AttributeError:
            self._condition_timeout_map = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._records = dict(self._records)

        if len(self._records) == 0:
            return

        logger.warning('Sync records with {} items'.format(len(self._records)))
        self.__sync_records()

    def add(self, query, *record_or_records):
        """
        Add new records to temp cache.
        :param query:
        :param record_or_records:
        :return:
        """
        key = self.__get_unique_cache_key(query)
        timeout = self.__get_timeout(query)

        if timeout:
            self._records[key].extend(record_or_records)
            self._timeouts[key] = self.__get_timeout(query)
            self._conditions[key] = query.get('where', {}) or {}

    def has(self, query):
        if not query:
            return False

        return self._cache_db.has(self.__get_unique_cache_key(query))

    def get(self, query):
        if not query:
            return None

        key = self.__get_unique_cache_key(query)
        return self._cache_db.get(key)

    def remove(self, *queries):
        """
        Stop tracking related queries in Redis
        """
        with QueryTracker(self._model, self._cache_db) as tracker:
            for q in queries:
                tracker.discard(q.get('where', {}))

    def clear(self):
        with QueryTracker(self._model, self._cache_db) as tracker:
            tracker.discard_all()

    def __sync_records(self):
        """
        Sync records to Redis server.
        :return:
        """
        with QueryTracker(self._model, self._cache_db) as tracker:
            for key, records in self._records.items():
                # tracker.track(key, records)
                tracker.track(key, self._conditions.get(key))
                self.__set_cond(key, records, self._timeouts.get(key))

    def __set_cond(self, cache_key, records, timeout=300):
        logger.debug('Cache records with key {}, timeout is {}'.format(cache_key, timeout))
        return self._cache_db.set(cache_key, records, timeout)

    def __get_timeout(self, query):
        where = query.get('where', {}) or {}

        if len(where) == 0:
            where['*'] = None

        key = '&'.join(sorted(where))
        return self._condition_timeout_map.get(key) or None

    def __get_unique_cache_key(self, query, no_fp=False):
        conditions = list()
        where = query.get('where', {})

        for k in sorted(where):
            v = where[k]
            if v is None:
                continue

            conditions.append((k, v))

        conditions = '&'.join('{}={}'.format(k, v) for k, v in conditions) or '*'

        if no_fp is True:
            return '{}_where_{}'.format(camel_to_underscore(self._model.__name__), conditions)

        query_fp = get_query_fingerprint(query)
        return '{}_where_{}_fp_{}'.format(camel_to_underscore(self._model.__name__), conditions, query_fp)


class QueryTracker(object):
    """
    Track all the cached conditions, delete them if needed.
    """

    def __init__(self, model, cache_db):
        self._cache_db = cache_db
        self._model = model
        self._tracker_container = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if len(self.tracker_container) > 0:
            logger.warning('Sync tracker {} with {} items'.format(self.tracker_key, len(self.tracker_container)))
            self._cache_db.set(self.tracker_key, self.tracker_container, 0)
        else:
            self._cache_db.delete(self.tracker_key)

    def track(self, key, where):
        logger.info('Track query with key: {}'.format(key))
        self.tracker_container[key] = where

    def discard(self, where):
        """
        Related query keys will be discarded

        Pool way to find related keys and delete them
        """
        try:
            exact_match = all(where.values())
            tip = 'Exact' if exact_match else 'Contained'

            for key in list(self.tracker_container.keys()):
                value = self.tracker_container[key]
                should_delete = False

                if exact_match is True:
                    if value == where:
                        should_delete = True
                else:
                    # Must be careful, have to delete all the related keys at last
                    for k, v in where.items():
                        if '__' in k and k in value:
                            should_delete = True
                            break

                        if v is None:
                            continue

                        if value.get(k) == v:
                            should_delete = True
                            break

                if should_delete is True:
                    logger.warning('[{}] Discard related condition key <{}>'.format(tip, key))
                    del self.tracker_container[key]
                    self._cache_db.delete(key)
        except Exception:
            return False

    def discard_all(self):
        """
        Remove all the related keys in Redis
        """
        logger.warning('Discard all the related keys for {}'.format(self.tracker_key))

        try:
            keys = list(self.tracker_container)
            self._cache_db.delete_many(*keys)
            self.tracker_container.clear()
            return True
        except Exception as err:
            logger.error(err)
            return False

    @property
    def tracker_container(self):
        if self._tracker_container is None:
            self._tracker_container = self._cache_db.get(self.tracker_key) or dict()

        return self._tracker_container

    @property
    def tracker_key(self):
        return 'query_tracker_for_{}'.format(camel_to_underscore(self._model.__name__))


__all__ = ['query_cache']
