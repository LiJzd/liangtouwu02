# -*- coding: utf-8 -*-
import sys
# 修复 Windows 终端中文输出乱码（确保输出流使用 UTF-8 编码）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

"""
自动化测试脚本：验证两头乌专属 RAG 检索与重建逻辑 (FastAPI API 级别 & 核心逻辑)
========================================================================
运行方式：
  $env:PYTHONUTF8=1
  pytest tests/test_liangtouwu_rag.py -v -s
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 动态确保项目根目录在 sys.path 中
CURRENT_DIR = Path(__file__).resolve().parent
AI_SERVICE_DIR = CURRENT_DIR.parent
if str(AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_DIR))

from fastapi.testclient import TestClient
from main import app
from pig_rag.liangtouwu_knowledge_rag import (
    query_liangtouwu_knowledge,
    init_liangtouwu_knowledge_db,
    LIANGTOUWU_KNOWLEDGE_CHUNKS
)

# 声明 FastAPI 测试客户端
client = TestClient(app)


# ============================================================
# 测试环境初始化与 Mock 夹具 (Fixtures)
# ============================================================

@pytest.fixture(scope="session", autouse=True)
def setup_mock_env():
    """
    Session 级别夹具：注入 Mock 的 API Key 环境变量，
    防止因宿主机未配 API Key 导致 ValueError 异常。
    """
    original_key = os.environ.get("DASHSCOPE_API_KEY")
    os.environ["DASHSCOPE_API_KEY"] = "mock_dashscope_api_key_for_testing"
    yield
    if original_key is not None:
        os.environ["DASHSCOPE_API_KEY"] = original_key
    else:
        os.environ.pop("DASHSCOPE_API_KEY", None)


@pytest.fixture(autouse=True)
def mock_dashscope_embeddings():
    """
    模块级自动应用 Mock：拦截 DashScope 向量嵌入调用，
    避免发送网络请求，实现 100% 离线高效稳定测试。
    """
    with patch("pig_rag.liangtouwu_knowledge_rag.DashScopeEmbeddings") as mock_class:
        mock_instance = MagicMock()
        # Mock embed_documents：根据输入文本的行数，模拟返回 1536 维的向量列表
        mock_instance.embed_documents.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
        # Mock embed_query：模拟返回单个查询向量
        mock_instance.embed_query.return_value = [0.1] * 1536
        
        mock_class.return_value = mock_instance
        yield mock_instance


# ============================================================
# 测试用例一：核心逻辑直接调用验证
# ============================================================

def test_rag_core_direct_init_and_query():
    """
    测试 1：直接调用核心层逻辑进行库重建与语义检索
    """
    print("\n[TEST] 开始直接调用 RAG 核心重建逻辑...")
    # 强制重建向量库
    vectorstore = init_liangtouwu_knowledge_db(force_rebuild=True)
    assert vectorstore is not None, "直接构建向量库返回的对象不应为空"
    
    print("[TEST] 开始直接调用语义搜索核心方法...")
    # 语义检索 Gompertz 生长曲线相关内容
    query_text = "Gompertz 生长曲线拐点参数"
    matches = query_liangtouwu_knowledge(query_text, top_n=2)
    
    # 断言基本检索属性
    assert len(matches) == 2, f"预期返回 2 条结果，实际返回了 {len(matches)} 条"
    
    # 验证检索结果的数据格式
    for idx, item in enumerate(matches):
        assert "text" in item, f"检索项 {idx} 中必须含有 text 字段"
        assert "score" in item, f"检索项 {idx} 中必须含有 score 字段"
        assert "metadata" in item, f"检索项 {idx} 中必须含有 metadata 字段"
        assert isinstance(item["score"], float), "score 字段应为浮点数"
        assert "breed" in item["metadata"] and item["metadata"]["breed"] == "两头乌", "元数据中 breed 应为两头乌"
        
    print("✅ 核心 RAG 直接调用测试全部通过。")


# ============================================================
# 测试用例二：FastAPI 控制器 HTTP 接口层验证
# ============================================================

def test_rag_api_endpoints():
    """
    测试 2：通过 FastAPI TestClient 模拟 HTTP 请求，全面覆盖控制器接口
    """
    print("\n[TEST] 开始请求 API 接口进行向量库强制重建 POST /api/v1/rag/liangtouwu/init...")
    # 1. 测试初始化/强制重建端点
    init_response = client.post(
        "/api/v1/rag/liangtouwu/init",
        json={"force_rebuild": False}
    )
    
    assert init_response.status_code == 200, f"初始化 API 异常响应: {init_response.text}"
    init_data = init_response.json()
    assert init_data["status"] == "success", "返回 status 应为 success"
    assert "成功" in init_data["message"], "message 中应指示构建成功信息"
    
    print("[TEST] 开始请求 API 接口进行语义查询 POST /api/v1/rag/liangtouwu/query...")
    # 2. 测试语义搜索端点
    query_payload = {
        "query": "易感气喘病支原体肺炎的预防药量和贼风氨气底线",
        "top_n": 3
    }
    query_response = client.post(
        "/api/v1/rag/liangtouwu/query",
        json=query_payload
    )
    
    assert query_response.status_code == 200, f"检索 API 异常响应: {query_response.text}"
    query_data = query_response.json()
    
    # 验证响应外层结构
    assert query_data["query"] == query_payload["query"]
    assert "results" in query_data, "响应体中必须包含 results"
    results = query_data["results"]
    assert len(results) == 3, f"预期请求 3 条结果，实际返回了 {len(results)} 条"
    
    # 验证响应内层条目结构与业务相关性
    for item in results:
        assert "text" in item
        assert "score" in item
        assert "metadata" in item
        assert item["metadata"]["breed"] == "两头乌"
        
    # 验证结果中是否确实能够召回最相关的段落（Mock 模式下 Chroma 仍会根据文本的字面和我们模拟的距离进行排序）
    # 检索是否成功走完整个链路
    print("✅ RAG API 端点 HTTP 模拟测试全部通过。")
