# -*-coding: utf-8-*-
# Author : Christopher Lee
# License: Apache License
# File   : util.py
# Date   : 2017-05-15 15-31
# Version: 0.0.1
# Description: description of this file.

import logging

import os
from functools import wraps
from werkzeug.contrib.cache import FileSystemCache

from .factory import RedisCacheFactory

logger = logging.getLogger(__name__)

__version__ = '0.0.1'
__author__ = 'Chris'


def output_cache(timeout=60, ignore_outputs=None, custom_cache_key='', cache_type='redis', **cache_options):
    """
    A cache wrapper that caches output of a function in the specified cache system.
    Note: the arguments of a function must be serializable to pickle.

    Improve: 2 times faster than the old implementation.

    Examples:
    1. Default with Redis cache:

    @output_cache(timeout=120, cache_type='redis')
    def function_foo(*args, **kwargs):
        pass

    2. With file cache:

    @output_cache(timeout=120, cache_type='file', cache_dir='/path/to/cache_dir/')
    def function_bar(*args, **kwargs):
        pass

    3. With custom key template:
    @output_cache(custom_cache_key='function_spam_{x}_{y}_{args}')
    def function_spam(x, y, *args, **kwargs):
        pass

    :param timeout: int, default key timeout
    :param ignore_outputs: list, ignored outputs won't be cached
    :param custom_cache_key: str template, define your own cache key
    :param cache_type: str, support **Redis** cache and **FileSystem** cache
    :param cache_options: dict, keyword arguments will be passed to `werkzeug.contrib.cache.RedisCache`
     or `werkzeug.contrib.cache.FileSystemCache` object.
            1. RedisCache(self, host='localhost', port=6379, password=None, db=0,
                        default_timeout=300, key_prefix=None, **kwargs)
            2. FileSystemCache(cache_dir, threshold=500, default_timeout=300, mode=0o600)
    :return: output of the wrapped function
    """
    try:
        list(iter(ignore_outputs))
    except:
        ignore_outputs = list()

    def make_custom_cache_key(func, *args, **kwargs):
        from collections import namedtuple
        import inspect

        # Get signatures of all the args and kwargs
        full_args = dict()
        spec = inspect.getfullargspec(func)
        NamedArgs = namedtuple('NamedArgs', spec.args)
        named_args = NamedArgs(*args[:len(spec.args)])
        full_args.update(named_args._asdict())
        full_args[spec.varargs] = args[len(spec.args):]
        full_args.update(kwargs)

        return custom_cache_key.format(**full_args)

    def make_cache_key(func, *args, **kwargs):
        """
        Warning: in order to generate a default unique key for each object,
        the method `__repr__` or `__str__` must be overridden
        to identify the object. BTW, custom cache can be defined to replace
        the default one.
        """
        import pickle
        import inspect
        import hashlib

        if custom_cache_key:
            return make_custom_cache_key(func, *args, **kwargs)

        mod = inspect.getmodule(func)
        name = '{}.{}.{}'.format(cache_type, os.path.splitext(os.path.split(mod.__file__)[-1])[0], func.__name__)
        items = tuple(str(x) for x in args) + tuple(sorted((k, str(v)) for k, v in kwargs.items()))

        try:
            hash_key = hashlib.md5(pickle.dumps(items)).hexdigest()
            return '{}_{}'.format(name, hash_key)
        except (pickle.PickleError, pickle.PicklingError):
            raise ValueError('Arguments of the function `{}` must be serializable'.format(func.__name__))

    def get_cache_db():
        if cache_type.lower() == 'redis':
            return RedisCacheFactory().make_redis_cache(from_db='default', **cache_options)
        elif cache_type.lower() == 'file':
            return FileSystemCache(**cache_options)

        raise ValueError('Unsupported cache type: {}'.format(cache_type))

    def cache_get(key):
        logger.debug('Load result from {} cache with key `{}`'.format(cache_type, key))
        cache_db = get_cache_db()
        return cache_db.get(key)

    def cache_set(key, output):
        if output is None:
            return output

        if output in ignore_outputs:
            logger.warning('Output {} is in `ignored outputs`, ignore it'.format(output))
            return output

        print('Cache key is: {}'.format(key))
        logger.debug('Dump output result to {} cache with key `{}`'.format(cache_type, key))
        cache_db = get_cache_db()
        cache_db.set(key, output, timeout)

        return output

    def decorate_func(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            cache_key = make_cache_key(func, *args, **kwargs)
            cached_obj = cache_get(cache_key)

            return cached_obj if cached_obj is not None else cache_set(cache_key, func(*args, **kwargs))

        return inner_wrapper

    return decorate_func
