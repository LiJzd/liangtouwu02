# -*- coding: utf-8 -*-
"""
v1/agents/base_graph.py
LangGraph 核心状态空间定义与专家智能体路由图网络编译骨架
"""

import logging
from typing import Annotated, Sequence, TypedDict, List
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BaseGraph")

class AgentState(TypedDict):
    """
    LangGraph 核心全局强类型状态空间，继承自 TypedDict
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]  # 消息轨迹，自动追加模式
    current_agent: str                                       # 当前激活的专家智能体标识
    schema_metadata: dict                                    # 数据库表元数据，Text-to-SQL 使用
    query_context: dict                                      # RAG 召回与上下文暂存区
    errors: List[dict]                                       # 运行期错误轨迹记录
    client_id: str                                           # 客户端连接标识
    user_id: str                                             # 用户编号
    is_ammonia_demo: bool                                    # 仿真剧本：氨气演示标志位
    is_simulation_demo: bool                                 # 仿真剧本：一般模拟告警标志位
    metadata: dict                                           # 存储额外的仿真或调用元数据
    final_answer: str                                        # 最终生成的应答文本
    image_base64: str                                        # 最终生成的 Base64 图片，如监控截图
    image_key: str                                           # 抓拍图片的缓存键

# ============================================================
# 导入 9 大物理专家节点
# ============================================================

from v1.agents.nodes.supervisor_node import supervisor_node
from v1.agents.nodes.vet_node import vet_node
from v1.agents.nodes.data_node import data_node
from v1.agents.nodes.perception_node import perception_node
from v1.agents.nodes.growth_curve_node import growth_curve_node
from v1.agents.nodes.hardware_node import hardware_node
from v1.agents.nodes.briefing_node import briefing_node
from v1.agents.nodes.direct_reply_node import direct_reply_node
from v1.agents.nodes.fallback_node import fallback_node

# ============================================================
# 构建并实例化 StateGraph 图拓扑网络
# ============================================================

# 使用强类型状态空间实例化 StateGraph
graph = StateGraph(AgentState)

# 添加所有的 9 个物理节点
graph.add_node("supervisor_node", supervisor_node)
graph.add_node("vet_node", vet_node)
graph.add_node("data_node", data_node)
graph.add_node("perception_node", perception_node)
graph.add_node("growth_curve_node", growth_curve_node)
graph.add_node("hardware_node", hardware_node)
graph.add_node("briefing_node", briefing_node)
graph.add_node("direct_reply_node", direct_reply_node)
graph.add_node("fallback_node", fallback_node)

# 设置意图分析分发节点为图的默认入口点 (Entry Point)
graph.set_entry_point("supervisor_node")

# 编写条件路由边判定逻辑 (Conditional Router)
def route_agent(state: AgentState) -> str:
    """
    根据 current_agent 状态的值动态匹配下一跳专家节点
    """
    agent = state.get("current_agent")
    
    agent_mapping = {
        "vet": "vet_node",
        "data": "data_node",
        "perception": "perception_node",
        "growth_curve": "growth_curve_node",
        "hardware": "hardware_node",
        "briefing": "briefing_node",
        "direct_reply": "direct_reply_node",
        "fallback": "fallback_node"
    }
    
    target = agent_mapping.get(agent, "fallback_node")
    logger.info(f"--- [Router] 根据 current_agent={agent} 路由跳转至目标节点: {target} ---")
    return target

# 将 supervisor_node 的条件边路由指向所有分支
graph.add_conditional_edges(
    "supervisor_node",
    route_agent,
    {
        "vet_node": "vet_node",
        "data_node": "data_node",
        "perception_node": "perception_node",
        "growth_curve_node": "growth_curve_node",
        "hardware_node": "hardware_node",
        "briefing_node": "briefing_node",
        "direct_reply_node": "direct_reply_node",
        "fallback_node": "fallback_node"
    }
)

# 普通边连接：所有处理节点在完成动作后，出口无条件指向图终点 END
graph.add_edge("vet_node", END)
graph.add_edge("data_node", END)
graph.add_edge("perception_node", END)
graph.add_edge("growth_curve_node", END)
graph.add_edge("hardware_node", END)
graph.add_edge("briefing_node", END)
graph.add_edge("direct_reply_node", END)
graph.add_edge("fallback_node", END)

# 编译图生成最终可运行的引擎实例并导出
compiled_graph = graph.compile()

# ============================================================
# 4. 提供外部执行的高阶接口
# ============================================================

async def execute_agent_graph(input_state: dict) -> dict:
    """
    外部调用异步图入口，运行图并返回最终的状态字典
    """
    logger.info("=== 异步调用专家状态图引擎启动 ===")
    return await compiled_graph.ainvoke(input_state)

if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage
    
    async def test_graph():
        print("=== [测试] base_graph 拓扑链路自我验证 ===")
        
        # 模拟外部输入状态
        test_state = {
            "messages": [HumanMessage(content="查询生猪的预测生长轨迹 PIG001")],
            "current_agent": None,
            "schema_metadata": {},
            "query_context": {},
            "errors": [],
            "client_id": "test_client",
            "user_id": "test_user",
            "is_ammonia_demo": False,
            "is_simulation_demo": False,
            "metadata": {},
            "final_answer": "",
            "image_base64": "",
            "image_key": ""
        }
        
        # 运行图并获取执行结果状态
        res = await execute_agent_graph(test_state)
        print("\n=== 执行完毕 ===")
        print(f"路由分发专家智能体：{res.get('current_agent')}")
        print(f"最终输出答复：{res.get('final_answer')}")

    asyncio.run(test_graph())
