# -*- coding: utf-8 -*-
"""
v1/db/milvus_client.py
本地 Milvus Lite 数据库初始化与客户端连接管理模块
"""

import os
from pymilvus import MilvusClient, DataType

# 连接本地数据库的绝对路径，确保不同上下文中指向相同的 milvus_pig_rag.db
DB_FILE_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "milvus_pig_rag.db"))

def get_milvus_client() -> MilvusClient:
    """
    获取单例本地 MilvusClient 实例
    """
    return MilvusClient(DB_FILE_PATH)

def init_milvus_collections(force_rebuild: bool = False):
    """
    初始化构建两只生猪生长及全生命周期的 Milvus 向量集合
    """
    client = get_milvus_client()
    
    if force_rebuild:
        print("[Milvus] 正在物理清除旧有向量集合...")
        if client.has_collection("pig_growth_collection"):
            client.drop_collection("pig_growth_collection")
        if client.has_collection("pig_lifecycle_collection"):
            client.drop_collection("pig_lifecycle_collection")

    # 1. 初始化生猪生长轨迹集合 (pig_growth_collection)
    if not client.has_collection("pig_growth_collection"):
        print("[Milvus] 正在创建 pig_growth_collection...")
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
        schema.add_field(field_name="breed", datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="age_days", datatype=DataType.INT64)
        schema.add_field(field_name="weight_kg", datatype=DataType.DOUBLE)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2048)

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE"
        )
        
        client.create_collection(
            collection_name="pig_growth_collection",
            schema=schema,
            index_params=index_params
        )
        print("[Milvus] pig_growth_collection 创建成功。")

    # 2. 初始化生猪全生命周期时序切片集合 (pig_lifecycle_collection)
    if not client.has_collection("pig_lifecycle_collection"):
        print("[Milvus] 正在创建 pig_lifecycle_collection...")
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=64, is_primary=True)
        schema.add_field(field_name="pig_id", datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="breed", datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="slice_month", datatype=DataType.INT64)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2048)
        schema.add_field(field_name="lifecycle_json", datatype=DataType.VARCHAR, max_length=8192)

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE"
        )
        
        client.create_collection(
            collection_name="pig_lifecycle_collection",
            schema=schema,
            index_params=index_params
        )
        print("[Milvus] pig_lifecycle_collection 创建成功。")

if __name__ == "__main__":
    print(f"本地 Milvus 存储路径: {DB_FILE_PATH}")
    init_milvus_collections(force_rebuild=True)
    print("=== Milvus 初始化完毕 ===")
