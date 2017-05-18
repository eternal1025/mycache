# -*-coding: utf-8-*-
# Author : Christopher Lee
# License: Apache License
# File   : utils.py
# Date   : 2017-05-18 09-01
# Version: 0.0.1
# Description: description of this file.

import pickle
from string import ascii_uppercase, ascii_lowercase

import hashlib


ASCII_MAPPING = dict((k, '_{}'.format(v)) for k, v in zip(ascii_uppercase, ascii_lowercase))


def camel_to_underscore(key):
    """
    Fast way to converse camel style to underscore style
    :param key: word to be converted
    :return: str
    """
    return ''.join(ASCII_MAPPING.get(x) or x for x in key).strip('_')


def get_query_fingerprint(query, hash_method='md5'):
    """
    Generate a unique fingerprint for the given query

    :return: hash value
    """
    sorted_query = []
    for k in sorted(query.keys()):
        value = query.get(k)
        try:
            sorted_query.append((k, sorted(value)))
        except TypeError:
            sorted_query.append((k, value))

    method = getattr(hashlib, hash_method)
    return method(pickle.dumps(sorted_query)).hexdigest()


if __name__ == '__main__':
    d = {'select': ['folder_id', 'icon_url', 'name', 'create_at'], 'limit': 20, 'descending': True, 'where': {},
         'order_by': ['folder_id', ]}

    print(get_query_fingerprint(d))
