# -*-coding: utf-8-*-
# Author : Christopher Lee
# License: Apache License
# File   : test_query_cache.py
# Date   : 2017-05-18 09-08
# Version: 0.0.1
# Description: description of this file.

import logging

import datetime
from db_util import mysql_query, mysql_execute

from dataobj import IntField, DatetimeField
from dataobj import Model
from dataobj import StrField
from mycache import query_cache

logging.basicConfig(level=logging.DEBUG)

URL = 'mysql://root:chris@localhost:3306/yunos_new'


class CommonDao(object):
    @staticmethod
    def execute(sql, args):
        # print("execute:", sql, args)
        return mysql_execute(sql, args=args, mysql_url=URL, debug=True)

    @staticmethod
    def query(sql, args):
        # print("query:", sql, args)
        return mysql_query(sql, args=args, mysql_url=URL, debug=True)


@query_cache
class Folder(Model):
    folder_id = IntField(db_column='id', primary_key=True, auto_increment=True)
    name = StrField(db_column='name', default='新建文件夹', max_length=255)
    icon_url = StrField(not_null=False, max_length=1024)
    create_at = DatetimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'folder'
        dao_class = CommonDao
        cache_conditions = {
            '*': 3600,
            'folder_id': 3600,
            'name': 3600,
            'folder_id__lt': 3600,
            'folder_id__gt + name__contains': 3500
        }


def test_query():
    # print(Folder.objects.count())
    for x in range(30, 35):
        Folder.objects.get(folder_id=x)
    # print()

    results = Folder.objects.all().order_by('folder_id', descending=True).limit(5)
    print("Length of results: {}".format(len(results)))
    print("First item of results: {}".format(results.first()))
    print("Last item of results: {}".format(results.last()))
    print("List slicing: {}".format(results[:4]))


def test_dump_new(i):
    # Folder.objects.all().order_by("folder_id").last()
    folder = Folder()
    folder.name = '新建文件夹_{}'.format(i)
    folder.icon_url = "https://img.moviewisdom.cn/folder_icon_{}.png".format(i)
    folder.dump()
    # print(Folder.objects.all().order_by("folder_id", descending=True).first())


def test_update():
    last_id = Folder.objects.all().order_by("folder_id", descending=True).first().folder_id
    folder = Folder.objects.get(folder_id=last_id)
    print(folder)

    print(folder.update(name="测试更新-L".format(folder.folder_id, datetime.datetime.now().isoformat())))
    # folder = Folder.objects.all().order_by("folder_id", descending=True).first()
    folder = Folder.objects.get(folder_id=last_id)
    print(folder)


def test_delete():
    last_id = Folder.objects.all().order_by("folder_id").last().folder_id
    folder = Folder.objects.get(folder_id=last_id)
    print(folder)

    print(folder.delete())
    folder = Folder.objects.all().order_by("folder_id").last()
    print(folder)


def test_multi_operations():
    # 首先创建 10 个文件夹
    # for _ in range(5):
    #     test_dump_new("Chris, {}".format(_))

    # 然后采用各种方式加载这些文件夹
    for x in Folder.objects.filter(folder_id__gt=8, name__contains='Chris'):
        print(x)

    print()
    # test_dump_new('Chris, new')
    f = Folder.objects.all().order_by("folder_id").last()
    # f.update(name='Chris Updated')
    f.delete()


def test_all_cache():
    Folder.objects.all_cache()
    print(Folder.objects.get(name="新建文件夹_新增"))
    print(Folder.objects.get(folder_id=10))
    print(Folder.objects.filter(name="新建文件夹_新增").order_by('folder_id', descending=True).limit(2, 100)[:])
    print(Folder.objects.filter(name="新建文件夹_新增")[:])


def test_clear_cache():
    Folder.objects.clear_cache()


if __name__ == '__main__':
    # test_query()
    # for _ in range(20):
    #     test_dump_new('X')
    # test_update()
    #
    # for _ in range(20):
    #     test_delete()
    # test_multi_operations()
    test_all_cache()
    test_clear_cache()
