# -*-coding: utf-8-*-
# Author : Christopher Lee
# License: Apache License
# File   : test_output_cache.py
# Date   : 2017-05-15 16-03
# Version: 0.0.1
# Description: description of this file.

from mycache.output import output_cache


@output_cache(timeout=100, threshold=10, cache_dir='cache_db', cache_type='file')
def test_cache_wrapper(a, b, c):
    return a * b + c


@output_cache(timeout=100, threshold=10, cache_dir='cache_db', cache_type='file')
def test_file_cache(x, y, z):
    time.sleep(0.1)
    return x * y + z


class CacheFoo(object):
    def __init__(self, a, b):
        self._a = a
        self._b = b

    def __repr__(self):
        return '<CacheFoo a={}, b={}>'.format(self._a, self._b)

    @output_cache(timeout=100, threshold=10, cache_dir='cache_db', cache_type='file')
    def test_cache_wrapper(self, *args):
        time.sleep(1)
        return self._a * self._b + sum(args)


@output_cache(custom_cache_key='test_fast_cache_{x}_{y}_{z}_{f}_{mn}')
def test_fast_cache(x, y, z, **kwargs):
    print(x, y, z, kwargs)
    return x * y * z


if __name__ == '__main__':
    import time

    start = time.time()

    foo = CacheFoo(10, 20)

    for _ in range(1):
        # print(test_cache_wrapper(10, 20, 30))
        # print(foo.test_cache_wrapper(10, 20, 30))
        # print(test_file_cache(10, 20, 30))
        test_fast_cache(10, 21, 30, f=100)

    print('耗时：{}'.format(time.time() - start))
