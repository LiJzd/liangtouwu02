# 🧠 Python 依赖深度解析与重构诊断报告
**生成时间**：2026-05-20 13:25:44  
**扫描目录**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic`  

---

## 📊 1. 整体度量与耦合度概览
以下表格展示了递归扫描的所有 Python 文件的基本物理度量以及对核心组件（`multi_agent_core` 和 `bot_tools`）的耦合情况：

| 文件名 | 大小 (KB) | 物理行数 | 定义的类数 | 定义的顶级函数数 | `multi_agent_core` 强引用数 | `bot_tools` 强引用数 | 耦合评级 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `__init__.py` | 0.06 | 2 | 0 | 0 | 0 | 0 | 🟢 极松耦合 (Low) |
| `agent_debug_controller.py` | 6.16 | 162 | 1 | 5 | 0 | 0 | 🟢 极松耦合 (Low) |
| `agent_simulation_controller.py` | 1.4 | 43 | 0 | 2 | 0 | 0 | 🟢 极松耦合 (Low) |
| `agent_simulation_service.py` | 20.29 | 466 | 2 | 1 | 4 | 1 | 🟡 中度耦合 (Medium) |
| `bot_agent.py` | 15.82 | 470 | 0 | 24 | 0 | 0 | 🟢 极松耦合 (Low) |
| `bot_controller.py` | 3.21 | 95 | 0 | 4 | 0 | 0 | 🟢 极松耦合 (Low) |
| `bot_scheduler.py` | 1.94 | 66 | 0 | 2 | 0 | 0 | 🟢 极松耦合 (Low) |
| `bot_tools.py` | 48.17 | 1263 | 1 | 24 | 0 | 0 | 🟢 极松耦合 (Low) |
| `central_agent_controller.py` | 0.76 | 21 | 0 | 1 | 0 | 0 | 🟢 极松耦合 (Low) |
| `central_agent_core.py` | 22.97 | 658 | 1 | 14 | 0 | 1 | 🟡 中度耦合 (Medium) |
| `iot_controller.py` | 5.87 | 168 | 3 | 2 | 0 | 0 | 🟢 极松耦合 (Low) |
| `multi_agent_controller.py` | 9.49 | 255 | 0 | 5 | 5 | 0 | 🟡 中度耦合 (Medium) |
| `multi_agent_core.py` | 71.5 | 1215 | 12 | 3 | 0 | 15 | 🔴 高度耦合 (High 🚨) |
| `perception_controller.py` | 22.76 | 624 | 1 | 14 | 0 | 0 | 🟢 极松耦合 (Low) |
| `pig_inspection_controller.py` | 14.91 | 367 | 3 | 10 | 2 | 0 | 🟡 中度耦合 (Medium) |
| `voice_to_text.py` | 3.54 | 97 | 0 | 3 | 0 | 0 | 🟢 极松耦合 (Low) |

---

## 🔍 2. 核心重构坏味道诊断 (Refactoring Smells)
### 🚨 2.1 大文件/大模块 (Large File Smell)
以下文件物理行数超过 500 行，内部逻辑庞杂，违反了“单一职责原则 (SRP)”，建议进行模块拆分：

- **`bot_tools.py`** (1263 行, 48.17 KB)
- **`central_agent_core.py`** (658 行, 22.97 KB)
- **`multi_agent_core.py`** (1215 行, 71.5 KB)
- **`perception_controller.py`** (624 行, 22.76 KB)


### 🚨 2.2 核心模块强耦合 (High Coupling Smell)
以下文件与 `multi_agent_core` 或 `bot_tools` 存在严重的强引用耦合。直接引用具体实体（如类、函数）会导致“修改连锁反应 (Ripple Effect)”，增加系统脆弱性：

- **`multi_agent_core.py`**：引用 `multi_agent_core` 共 0 次，引用 `bot_tools` 共 15 次。


### ⚠️ 2.3 双向循环依赖风险 (Circular Dependency Risk)
检测到以下模块之间存在显式的双向或循环导入引用，这容易导致 Python 动态导入时的 `ImportError` 隐患，且使模块无法解耦独立测试：

- **⚠️ 核心引用**：`multi_agent_core.py` ➡️ `bot_tools.py` 单向直接引用。



---

## 📁 3. 模块深度诊断详情
### 📄 3.1 `__init__.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\__init__.py`
- **文件大小**：0.06 KB | **物理行数**：2 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 0 个)</summary>

*(未定义类)*
*(未定义顶级函数)*
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.2 `agent_debug_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\agent_debug_controller.py`
- **文件大小**：6.16 KB | **物理行数**：162 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 1 个, 顶级函数: 5 个)</summary>

#### 定义的类：
- **`class RichTraceHandler`**：包含方法 -> `__init__()`, `on_llm_new_token()`, `on_agent_action()`, `on_tool_end()`, `on_agent_finish()`, `get_thoughts()`
#### 定义的顶级函数：
- `get_or_create_queue()`
- `push_debug_event()`
- `cleanup_queue()`
- `agent_trace_stream()`
- `clear_debug_queue()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.3 `agent_simulation_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\agent_simulation_controller.py`
- **文件大小**：1.4 KB | **物理行数**：43 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 2 个)</summary>

*(未定义类)*
#### 定义的顶级函数：
- `ingest_simulation()`
- `trigger_mock_alert()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.4 `agent_simulation_service.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\agent_simulation_service.py`
- **文件大小**：20.29 KB | **物理行数**：466 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 2 个, 顶级函数: 1 个)</summary>

#### 定义的类：
- **`class CacheEntry`**：包含方法 -> 无
- **`class AgentSimulationService`**：包含方法 -> `ingest()`, `_normalize_event()`, `_evaluate_findings()`, `_build_cache_key()`, `_build_fingerprint()`, `_get_duplicate()`, `_update_cache()`, `_build_agent_prompt()`, `_derive_alert_type()`, `_derive_risk()`, `_build_announcement()`, `_extract_alert_payload()`
#### 定义的顶级函数：
- `get_orchestrator()`
</details>

#### 🔗 强引用依赖详情 (5 次引用)
| 行号 | 依赖模块 | 引用实体类型 | 引用实体名称 | 强引用代码片段 |
| :---: | :--- | :--- | :--- | :--- |
| 41 | `multi_agent_core` | Class | `MultiAgentOrchestrator` | `_ORCHESTRATOR: Optional[MultiAgentOrchestrator] = None` |
| 45 | `multi_agent_core` | Class | `MultiAgentOrchestrator` | `def get_orchestrator() -&gt; MultiAgentOrchestrator:` |
| 48 | `multi_agent_core` | Class | `MultiAgentOrchestrator` | `_ORCHESTRATOR = MultiAgentOrchestrator()` |
| 113 | `multi_agent_core` | Class | `AgentContext` | `context = AgentContext(` |
| 201 | `bot_tools` | Function | `tool_publish_alert` | `alert_result = await tool_publish_alert(json.dumps(force_payload, ensure_ascii=False))` |


### 📄 3.5 `bot_agent.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\bot_agent.py`
- **文件大小**：15.82 KB | **物理行数**：470 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 24 个)</summary>

*(未定义类)*
#### 定义的顶级函数：
- `_get_user_lock()`
- `ensure_user()`
- `_parse_time()`
- `_help_text()`
- `_format_tools()`
- `_subscribe_brief()`
- `_cancel_brief()`
- `_save_turn()`
- `_build_messages()`
- `_get_history()`
- `_fallback_reply()`
- `_call_central_agent()`
- `_is_danger()`
- `_is_help_query()`
- `_is_pig_topic()`
- `_strip_canned_prefix()`
- `_shorten_reply()`
- `_postprocess_reply()`
- `_reply_danger()`
- `_handle_message_locked()`
- `handle_message()`
- `build_daily_brief()`
- `enqueue_brief()`
- `is_due()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.6 `bot_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\bot_controller.py`
- **文件大小**：3.21 KB | **物理行数**：95 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 4 个)</summary>

*(未定义类)*
#### 定义的顶级函数：
- `handle_message_api()`
- `get_pending_outbox()`
- `mark_outbox()`
- `voice_to_text_api()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.7 `bot_scheduler.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\bot_scheduler.py`
- **文件大小**：1.94 KB | **物理行数**：66 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 2 个)</summary>

*(未定义类)*
#### 定义的顶级函数：
- `process_due_subscriptions()`
- `scheduler_loop()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.8 `bot_tools.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\bot_tools.py`
- **文件大小**：48.17 KB | **物理行数**：1263 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 1 个, 顶级函数: 24 个)</summary>

#### 定义的类：
- **`class Tool`**：包含方法 -> 无
#### 定义的顶级函数：
- `get_cached_image()`
- `tool()`
- `list_tools()`
- `_parse_args()`
- `_parse_json_maybe()`
- `_coerce_int()`
- `tool_current_time()`
- `tool_ping()`
- `tool_list_tools()`
- `tool_list_pigs()`
- `tool_get_pig_info_by_id()`
- `tool_query_pig_disease_rag()`
- `tool_query_env_status()`
- `_get_current_season()`
- `tool_query_similar_cases()`
- `tool_query_pig_health_records()`
- `_assess_pig_health()`
- `tool_query_pig_growth_prediction()`
- `tool_get_abnormal_pigs()`
- `tool_get_farm_stats()`
- `tool_publish_alert()`
- `tool_capture_pig_farm_snapshot()`
- `tool_control_iot_fan()`
- `tool_query_fan_status()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.9 `central_agent_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\central_agent_controller.py`
- **文件大小**：0.76 KB | **物理行数**：21 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 1 个)</summary>

*(未定义类)*
#### 定义的顶级函数：
- `chat()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.10 `central_agent_core.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\central_agent_core.py`
- **文件大小**：22.97 KB | **物理行数**：658 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 1 个, 顶级函数: 14 个)</summary>

#### 定义的类：
- **`class RichTraceHandler`**：包含方法 -> `__init__()`, `on_agent_action()`, `on_llm_start()`, `on_tool_end()`, `on_agent_finish()`, `on_llm_new_token()`, `_push_event()`
#### 定义的顶级函数：
- `_get_llm_config()`
- `_build_llm()`
- `_run_async()`
- `_build_lc_tools()`
- `_split_messages()`
- `_requires_tool()`
- `_extract_tool_error()`
- `_extract_final_answer()`
- `_run_agent_once()`
- `_push_error_event()`
- `_call_agent()`
- `_call_llm()`
- `_fallback_reply()`
- `generate_reply()`
</details>

#### 🔗 强引用依赖详情 (1 次引用)
| 行号 | 依赖模块 | 引用实体类型 | 引用实体名称 | 强引用代码片段 |
| :---: | :--- | :--- | :--- | :--- |
| 319 | `bot_tools` | Function | `list_tools` | `for tool in list_tools().values():` |


### 📄 3.11 `iot_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\iot_controller.py`
- **文件大小**：5.87 KB | **物理行数**：168 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 3 个, 顶级函数: 2 个)</summary>

#### 定义的类：
- **`class DeviceControlRequest`**：包含方法 -> 无
- **`class DeviceStatusResponse`**：包含方法 -> 无
- **`class IoTManager`**：包含方法 -> `__new__()`, `_get_serial()`, `send_command()`, `set_switch()`, `run_duration()`, `get_status()`
#### 定义的顶级函数：
- `control_device()`
- `get_device_status()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.12 `multi_agent_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\multi_agent_controller.py`
- **文件大小**：9.49 KB | **物理行数**：255 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 5 个)</summary>

*(未定义类)*
#### 定义的顶级函数：
- `get_orchestrator()`
- `chat_v2_preflight()`
- `chat_v2()`
- `chat_vanilla()`
- `transcribe_voice()`
</details>

#### 🔗 强引用依赖详情 (5 次引用)
| 行号 | 依赖模块 | 引用实体类型 | 引用实体名称 | 强引用代码片段 |
| :---: | :--- | :--- | :--- | :--- |
| 26 | `multi_agent_core` | Class | `MultiAgentOrchestrator` | `_orchestrator: MultiAgentOrchestrator \| None = None` |
| 29 | `multi_agent_core` | Class | `MultiAgentOrchestrator` | `def get_orchestrator() -&gt; MultiAgentOrchestrator:` |
| 33 | `multi_agent_core` | Class | `MultiAgentOrchestrator` | `_orchestrator = MultiAgentOrchestrator()` |
| 147 | `multi_agent_core` | Class | `AgentContext` | `context = AgentContext(` |
| 165 | `multi_agent_core` | Class | `AgentResult` | `result = AgentResult(` |


### 📄 3.13 `multi_agent_core.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\multi_agent_core.py`
- **文件大小**：71.5 KB | **物理行数**：1215 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 12 个, 顶级函数: 3 个)</summary>

#### 定义的类：
- **`class DashScopeNativeChat`**：包含方法 -> `__init__()`, `bind_tools()`, `_format_messages()`, `_astream()`, `_agenerate()`, `_generate()`, `_llm_type()`
- **`class AgentContext`**：包含方法 -> 无
- **`class AgentResult`**：包含方法 -> 无
- **`class SupervisorAgent`**：包含方法 -> `__init__()`, `route()`, `_llm_route()`
- **`class WorkerAgent`**：包含方法 -> `__init__()`, `get_tools()`, `_get_llm_config()`, `execute()`
- **`class VetAgent`**：包含方法 -> `__init__()`, `get_tools()`, `execute()`, `_execute_simulation_demo()`, `_execute_ammonia_demo()`, `_execute_omni()`, `_preprocess_image()`
- **`class DataAgent`**：包含方法 -> `__init__()`, `get_tools()`, `execute()`
- **`class PerceptionAgent`**：包含方法 -> `__init__()`, `get_tools()`
- **`class GrowthCurveAgent`**：包含方法 -> `__init__()`, `get_tools()`, `execute()`
- **`class HardwareAgent`**：包含方法 -> `__init__()`, `get_tools()`, `execute()`
- **`class BriefingAgent`**：包含方法 -> `__init__()`, `get_tools()`, `execute()`
- **`class MultiAgentOrchestrator`**：包含方法 -> `__init__()`, `execute()`
#### 定义的顶级函数：
- `_extract_text_from_response()`
- `_is_multimodal_model()`
- `_convert_to_dashscope_tool()`
</details>

#### 🔗 强引用依赖详情 (15 次引用)
| 行号 | 依赖模块 | 引用实体类型 | 引用实体名称 | 强引用代码片段 |
| :---: | :--- | :--- | :--- | :--- |
| 388 | `bot_tools` | Function | `list_tools` | `at = list_tools()` |
| 537 | `bot_tools` | Function | `tool_query_pig_disease_rag` | `rag_task = tool_query_pig_disease_rag(json.dumps({"query": query_text}, ensure_ascii=False))` |
| 538 | `bot_tools` | Function | `tool_query_env_status` | `env_task = tool_query_env_status("{}")` |
| 663 | `bot_tools` | Function | `list_tools` | `at = list_tools()` |
| 676 | `bot_tools` | Function | `tool_get_pig_info_by_id` | `raw_res = await tool_get_pig_info_by_id(json.dumps({"pig_id": p_id}))` |
| 707 | `bot_tools` | Function | `list_tools` | `at = list_tools()` |
| 715 | `bot_tools` | Function | `list_tools` | `at = list_tools()` |
| 750 | `bot_tools` | Function | `tool_get_pig_info_by_id` | `raw_info = await tool_get_pig_info_by_id(json.dumps({"pig_id": p_id}))` |
| 790 | `bot_tools` | Function | `tool_query_pig_growth_prediction` | `raw_pred = await tool_query_pig_growth_prediction(json.dumps({"pig_id": p_id}))` |
| 931 | `bot_tools` | Function | `list_tools` | `at = list_tools()` |
| 967 | `bot_tools` | Function | `tool_capture_pig_farm_snapshot` | `raw_res = await tool_capture_pig_farm_snapshot(json.dumps({"video_file": target_video}))` |
| 974 | `bot_tools` | Function | `_IMAGE_CACHE` | `img_base64 = _IMAGE_CACHE.get(img_key) if img_key else None` |
| 990 | `bot_tools` | Function | `tool_query_env_status` | `raw_env = await tool_query_env_status("{}")` |
| 1035 | `bot_tools` | Function | `list_tools` | `at = list_tools()` |
| 1054 | `bot_tools` | Function | `tool_get_farm_stats` | `raw = await tool_get_farm_stats("{}")` |


### 📄 3.14 `perception_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\perception_controller.py`
- **文件大小**：22.76 KB | **物理行数**：624 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 1 个, 顶级函数: 14 个)</summary>

#### 定义的类：
- **`class Base64ImageRequest`**：包含方法 -> 无
#### 定义的顶级函数：
- `suppress_stderr()`
- `get_yolo_model()`
- `get_id_model()`
- `get_detection_model()`
- `load_image_from_url()`
- `load_image_from_base64()`
- `parse_yolo_results()`
- `detect_from_url()`
- `detect_from_base64()`
- `detect_from_upload()`
- `generate_frames()`
- `stream_video()`
- `get_model_info()`
- `health_check()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。


### 📄 3.15 `pig_inspection_controller.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\pig_inspection_controller.py`
- **文件大小**：14.91 KB | **物理行数**：367 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 3 个, 顶级函数: 10 个)</summary>

#### 定义的类：
- **`class InspectionRequest`**：包含方法 -> 无
- **`class InspectionResponse`**：包含方法 -> 无
- **`class ErrorResponse`**：包含方法 -> 无
#### 定义的顶级函数：
- `_fmt_sse()`
- `_build_growth_curve_intent()`
- `_build_briefing_intent()`
- `_run_growth_curve_via_agent()`
- `_run_briefing_via_agent()`
- `generate_inspection_report()`
- `generate_inspection_report_stream()`
- `generate_farm_briefing()`
- `generate_farm_briefing_stream()`
- `health_check()`
</details>

#### 🔗 强引用依赖详情 (2 次引用)
| 行号 | 依赖模块 | 引用实体类型 | 引用实体名称 | 强引用代码片段 |
| :---: | :--- | :--- | :--- | :--- |
| 88 | `multi_agent_core` | Class | `AgentContext` | `context = AgentContext(` |
| 113 | `multi_agent_core` | Class | `AgentContext` | `context = AgentContext(` |


### 📄 3.16 `voice_to_text.py`
- **物理路径**：`c:\Users\lost\Desktop\两头乌\ai-service\v1\logic\voice_to_text.py`
- **文件大小**：3.54 KB | **物理行数**：97 行
<details>
<summary>🔍 点击展开查看定义的类与顶级函数 (类: 0 个, 顶级函数: 3 个)</summary>

*(未定义类)*
#### 定义的顶级函数：
- `voice_to_text()`
- `file_to_text()`
- `_transcribe_with_paraformer()`
</details>

#### 🔗 强引用依赖详情 (0 次引用)
🟢 该文件不依赖 `multi_agent_core` 和 `bot_tools`。



---

## 🛠️ 4. 架构演进与重构方案建议
基于上述诊断出的高耦合度依赖和坏味道，特建议以下几项核心重构对策，以实现模块间的松耦合和高可维护性：

### 💡 4.1 引入智能体与工具注册机制 (Registry Pattern)
- **现状**：各模块在需要调用某些 Bot 智能体或工具时，通过直接 `from multi_agent_core import ...` 或 `from bot_tools import ...` 强引用具体实体，造成强耦合。
- **对策**：
  1. 在底层库中实现一个轻量级的注册表组件（如 `AgentRegistry` 和 `ToolRegistry`）。
  2. 在 `multi_agent_core` 中只提供抽象的 `BaseAgent` 定义，各个具体智能体（如 `BotAgent`）启动时**动态注册**到 `AgentRegistry` 中。
  3. 业务消费方（如各种 Controller）统一通过 `AgentRegistry.get("agent_name")` 来获取实例，实现编译期解耦，运行时组装。

### 💡 4.2 提取接口与抽象基类 (Dependency Inversion Principle - DIP)
- **现状**：外部 Controller 深度依赖核心模块的内部方法。核心模块一旦修改，所有 Controller 都需要连锁修改。
- **对策**：
  1. 定义统一的业务接口基类（例如 `BaseController` 或 `IBotService`），规定必须要实现的核心生命周期方法。
  2. Controller 不直接引用 `multi_agent_core` 的具体对象，而是依赖 `IAgentService` 接口，通过构造函数注入（Dependency Injection）方式传入具体实现。

### 💡 4.3 彻底消除循环依赖
- **对策**：
  1. **层级切分**：将 `bot_tools` 和 `multi_agent_core` 中互相引用的部分进行分层。通常，底层的工具集不应该知道上层的智能体逻辑；如果工具需要智能体协作，应通过回调函数（Callback）或事件通知（Event Emitter）方式进行异步松耦合交互。
  2. **提取公用第三方依赖**：如果两者互相引用了某几个共有数据结构，应将这部分共有数据结构提取到独立的 `models.py` 或 `types.py` 文件中，使两者都单向依赖该纯净定义文件。

---
*(报告完毕。请研发团队依据此报告评估重构计划，提升系统整体高内聚、低耦合架构品质。)*