# -*-coding: utf-8-*-
# Author : Christopher Lee
# License: Apache License
# File   : test_output_cache.py
# Date   : 2017-05-15 16-03
# Version: 0.0.1
# Description: description of this file.

from yuanshi.smartrate.objctrl.common.mycache.src import output_cache
from yuanshi.smartrate.utils.single_context import single_module_context


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

    @output_cache(timeout=100, threshold=10, cache_dir='cache_db', cache_type='file')
    def test_cache_wrapper(self, *args):
        time.sleep(0.1)
        return self._a * self._b + sum(args)


@output_cache()
def test_fast_cache(x, y, z):
    time.sleep(0.1)
    return x * y * z


if __name__ == '__main__':
    with single_module_context():
        import time

        start = time.time()

        foo = CacheFoo(10, 20)

        for _ in range(1000):
            print(test_cache_wrapper(10, 20, 30))
            print(foo.test_cache_wrapper(10, 20, 30))
            print(test_file_cache(10, 20, 30))
            test_fast_cache(10, 20, 30)

        print('耗时：{}'.format(time.time() - start))
