# Bugfix Requirements Document

## Introduction

系统在加入生长曲线功能后，运行猪只检查时崩溃并抛出`NameError: name 'datetime' is not defined`错误。该错误发生在`pig_agent.py`的`build_dual_track_report`函数第282行，尝试调用`datetime.now()`时因缺少`datetime`模块导入而失败。这导致整个双轨检查报告生成流程中断，影响核心业务功能。

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `build_dual_track_report`函数执行到第282行尝试使用`datetime.now().strftime('%Y-%m-%d %H:%M:%S')`时 THEN 系统抛出`NameError: name 'datetime' is not defined`异常并崩溃

1.2 WHEN 用户通过`pig_inspection_controller.py`调用`_run_inspection`函数触发猪只检查流程时 THEN 整个报告生成流程因`datetime`未定义而中断，无法返回检查报告

1.3 WHEN 系统尝试生成报告时间戳时 THEN 因缺少必要的模块导入导致运行时错误

### Expected Behavior (Correct)

2.1 WHEN `build_dual_track_report`函数执行到第282行时 THEN 系统SHALL成功调用`datetime.now()`并正确格式化时间戳为`'%Y-%m-%d %H:%M:%S'`格式

2.2 WHEN 用户通过`pig_inspection_controller.py`调用`_run_inspection`函数触发猪只检查流程时 THEN 系统SHALL成功生成包含生长曲线预测和专家建议的完整双轨检查报告

2.3 WHEN 系统生成报告时 THEN 报告末尾SHALL包含正确格式化的生成时间戳（如：`*报告生成时间：2024-01-15 14:30:25*`）

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `pig_agent.py`中的其他函数（如`run_dual_track_inspection`、`_call_llm_for_diagnosis`等）执行时 THEN 系统SHALL CONTINUE TO正常运行，不受导入修改影响

3.2 WHEN 报告生成流程中的数值引擎计算、RAG检索、LLM诊断等其他步骤执行时 THEN 这些步骤SHALL CONTINUE TO按原有逻辑正常工作

3.3 WHEN 系统生成的报告内容（包括基础档案、预测曲线数据表格、数值引擎推演、AI专家诊断等章节）时 THEN 报告格式和内容SHALL CONTINUE TO保持与修复前完全一致（除时间戳能正常显示外）

3.4 WHEN `pig_agent.py`中已存在的其他datetime相关功能（如`run_farm_daily_briefing`函数中的日期处理）执行时 THEN 这些功能SHALL CONTINUE TO正常工作
