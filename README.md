# `mycache` 缓存包文档

整个缓存包提供了两大功能：
1. 为数据层对象提供了专用的缓存装饰器，从而追踪数据层对象的增删改查状态，并在需要时移除 Redis 中缓存的状态，确保 Redis 中的数据是数据库中最新的；
1. 为常规函数输出提供了缓存装饰器，该装饰器是一个通用的工具，可类似 `functools.lru_cache` 那样对几乎所有函数的输出结果进行缓存，提供基于 Redis 和文件系统的缓存模式。

# 数据层缓存工具说明

1. 基于 DataObjectsManager 增加对象的缓存；
2. 不提供基于全表缓存功能接口，查询进行后会自动缓存，无需强制调用全表缓存。即采用按需缓存的模式，不使用不缓存。

## 使用方法

1. 首先使用装饰器 `query_cache` 对原数据层对象包装；
2. 接下来，在数据层对象中添加需要缓存的和追踪的查询条件，示例如下：

    ```python
    @query_cache
    class Folder(Model):
        folder_id = IntField(db_column='id', primary_key=True, auto_increment=True)
        name = StrField(db_column='name', default='新建文件夹', max_length=255)
        icon_url = StrField(not_null=False, max_length=1024)
        create_at = DatetimeField(default=datetime.datetime.now)
    
        class Meta:
            table_name = 'folder'
            dao_class = CommonDao
         
            # 添加需要缓存的查询条件
            cache_conditions = {
                '*': 3600, # 对于不指定过滤条件进行全表查询的结果缓存
                'folder_id': 3600,
                'name': 3600,
                'name+folder_id': 3600
            }
    ```

## 查询工作流程

1. 首次执行查询时，会优先检查 Redis 中是否存在该条件对应的查询结果（由 `CacheManager.get` 负责查询并返回）；
2. 若上一步查询结果为 None，则表明没有缓存，进入下一步；否则直接返回查询结果；
3. 执行 SQL 查询，并将返回的结果（即数据层对象）缓存到 Redis 中（由 `CacheManager.set` 完成缓存过程，同时会在 `QueryTracker` 中记录对该条件对应 query 条件的追踪）；
4. 返回查询结果。

## 修改（增删改）工作流程

1. 首先将受影响的对象的 query 提交给 `CacheManager.remove()`，从而移除相关的 key，这样 Redis 就不存在旧的副本；
2. 然后将执行数据库的改动操作。


# 缓存 KEY 生成算法 
1. `ouput_cache`：为了便于生成某个函数唯一对应的缓存 key，采用了如下的算法：
    1. 获取被装饰函数的名称、模块名称作为前缀；
    2. 将函数所有的参数排序后使用 `pickle` 进行序列化；
    3. 将上一步得到的序列化字节使用 `hashlib.md5` 计算 HASH 签名；
    4. 拼接前缀和上一步的签名得到缓存 key。

1. `query_cache`：使用表名和基本查询条件作为 key 的前缀，然后再将查询结果的 HASH 签名计算出来，组合成唯一的 KEY。
    
## 使用说明

1. 使用 Redis 缓存
    
    ```python
    @output_cache(cache_type='redis')
    def test_fast_cache(x, y, z):
        time.sleep(0.1)
        return x * y * z
    ```

1. 使用文件缓存

    ```python
    @output_cache(timeout=100, threshold=10, cache_dir='cache_db', cache_type='file')
    def test_file_cache(x, y, z):
        time.sleep(0.1)
        return x * y + z
    ```
    

# 更新日志

## 2017-05-19 v0.2
1. 增加全表快速缓存接口，支持简单的缓存条件预先构建，新接口：`all_cache()` 和 `clear_cache`；
1. 更新测试代码及文档；
1. 针对 `limit` 和 `order_by` 的情况将不参与缓存了，实际中若表中数据发生变化，`limit` 和 `order_by` 条件执行后可能都会不同。

## 2017-05-18 v0.1

1. 将缓存工具包独立开来，并进行打包；
1. 初步支持对 `dataobj` 中的查询集合缓存功能；
1. 重构 `CacheManager` 以支持新版的 `dataobj` 数据库操作功能；
1. 文档更新完成；
1. 测试代码更新完成。