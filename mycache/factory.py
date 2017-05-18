# -*-coding: utf-8-*-
# Author : Christopher Lee
# License: Apache License
# File   : factory.py
# Date   : 2017-05-15 15-30
# Version: 0.0.1
# Description: cache instance factory

from functools import partial

from flask import g
from functools import wraps

from werkzeug.contrib.cache import RedisCache

__version__ = '0.0.1'
__author__ = 'Chris'


def lock(self, name, timeout=None, sleep=0.1, blocking_timeout=None,
         lock_class=None, thread_local=True):
    return self._client.lock(name,
                             timeout, sleep, blocking_timeout, lock_class, thread_local)


def add_lock_method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_db = func(*args, **kwargs)
        cache_db.lock = partial(lock, cache_db)
        return cache_db

    return wrapper


class RedisCacheFactory(object):
    """
    Cache factory.
    """
    __factory_instance = None
    __redis_instances = {}

    def __new__(cls, *args, **kwargs):
        if cls.__factory_instance is None:
            cls.__factory_instance = object.__new__(cls)

        return cls.__factory_instance

    @add_lock_method
    def make_redis_cache(self, from_db='default', **kwargs):
        try:
            # Use global cache instance.
            return {
                'default': g.default_redis_cache,
                'data_objects': g.data_objects_redis_cache
            }.get(from_db)
        except Exception as err:
            redis_id = 'redis.' + '_'.join(
                '{}({})'.format(k, kwargs.get(k)) for k in sorted(kwargs.keys()) if kwargs.get(k))

            if redis_id not in self.__redis_instances:
                self.__redis_instances[redis_id] = RedisCache(default_timeout=3600 * 12, **kwargs)

            return self.__redis_instances.get(redis_id)


if __name__ == '__main__':
    db = RedisCacheFactory().make_redis_cache()
    with db.lock('test'):
        import time

        print('Hello')
        time.sleep(2)
