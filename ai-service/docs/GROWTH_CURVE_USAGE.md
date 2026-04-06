# 生长曲线预测功能使用指南

## 概述

生长曲线预测功能是掌上明猪系统的核心AI能力之一，通过RAG（检索增强生成）技术、DTW（动态时间规整）算法和Gompertz生长模型，为养殖户提供精准的猪只生长趋势预测。

---

## 功能特点

### 1. 时间序列切片 (Timeline Slicing)
- 将历史猪只的生长数据按月份切片
- 每个切片作为独立的向量存储
- 确保时间对齐，避免"数据穿越"问题

### 2. DTW动态时间规整
- 计算当前猪只与历史猪只的生长轨迹相似度
- 支持时间轴的轻微平移和伸缩
- 使用Sakoe-Chiba窗口优化性能

### 3. Gompertz生长曲线拟合
- 使用生物生长方程: `W(t) = A * exp(-b * exp(-c * t))`
- 参数自动拟合，适应个体差异
- 生成平滑的预测曲线

### 4. 双轨架构报告
- **数值轨**: 精确的体重预测数据
- **认知轨**: AI专家诊断和干预建议

---

## API使用

### 方式1: 通过多智能体对话

```bash
curl -X POST "http://localhost:8000/api/v1/agent/chat/v2" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "farmer_001",
    "messages": [
      {
        "role": "user",
        "content": "查询猪只PIG001的生长曲线"
      }
    ]
  }'
```

**响应示例**:
```json
{
  "reply": "## 生猪个体生长趋势分析报告\n\n### 📌 基础生长档案\n- **猪只ID**：`PIG001`\n..."
}
```

### 方式2: 直接调用工具

```python
from v1.logic.bot_tools import tool_query_pig_growth_prediction
import asyncio
import json

async def predict_growth():
    # 方式A: 通过pig_id自动获取数据
    result = await tool_query_pig_growth_prediction(
        json.dumps({"pig_id": "PIG001"})
    )
    
    # 方式B: 手动提供数据
    result = await tool_query_pig_growth_prediction(
        json.dumps({
            "breed": "两头乌",
            "current_month": 3,
            "current_month_data": {
                "feed_count": 45,
                "feed_duration_mins": 300,
                "weight_kg": 45.0
            },
            "top_n": 3
        })
    )
    
    print(result)

asyncio.run(predict_growth())
```

### 方式3: 使用RAG系统

```python
from pig_rag.pig_lifecycle_rag import query_pig_growth_prediction

# 查询预测
result = query_pig_growth_prediction(
    breed="两头乌",
    current_month=3,
    current_month_data={
        "feed_count": 45,
        "feed_duration_mins": 300,
        "weight_kg": 45.0
    },
    top_n=3
)

print(result)
```

---

## 参数说明

### 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pig_id` | string | 否* | 猪只ID，提供后自动获取其他参数 |
| `breed` | string | 是* | 猪只品种（如"两头乌"、"杜洛克"） |
| `current_month` | int | 是* | 当前月龄 |
| `current_month_data` | object | 是* | 当前月份的数据 |
| `top_n` | int | 否 | 返回Top-K相似案例数量，默认3 |

*注: 提供`pig_id`时，其他参数可选；否则`breed`、`current_month`、`current_month_data`必填

### current_month_data 结构

```json
{
  "month": 3,                    // 月份（可选）
  "feed_count": 45,              // 进食次数
  "feed_duration_mins": 300,     // 进食时长（分钟）
  "water_count": 80,             // 饮水次数（可选）
  "water_duration_mins": 160,    // 饮水时长（可选）
  "weight_kg": 45.0              // 当前体重（kg）
}
```

### 输出格式

```json
{
  "query_context": "两头乌龄期3月",
  "top_matches": [
    {
      "matched_pig": "pig_lc_005",
      "similarity_distance": 0.1234,
      "historical_future_track": [
        {
          "month": 4,
          "feed_count": 48,
          "feed_duration_mins": 310,
          "weight_kg": 60.0,
          "status": "生长中"
        },
        // ... 更多月份数据
      ]
    }
  ]
}
```

---

## 报告解读

### 1. 基础生长档案
```markdown
### 📌 基础生长档案
- **猪只ID**：`PIG001`
- **品种**：金华两头乌
- **当前日龄**：90 天 (约 3 月龄)
- **当前称重**：**35.50 kg**
- **模型偏离度**：`+2.50%`
```

**解读**:
- 模型偏离度为正: 生长速度快于标准
- 模型偏离度为负: 生长速度慢于标准
- 偏离度 < 5%: 正常范围
- 偏离度 > 15%: 需要关注

### 2. 预测生长曲线数据
```markdown
### 📊 预测生长曲线数据 (Monthly)
| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |
|---|---:|---|
| 3 | 35.50 | **当前实测** |
| 4 | 45.0 | 后期预测 |
| 5 | 55.0 | 后期预测 |
| 6 | 65.0 | 后期预测 |
```

**解读**:
- 表格数据可直接用于ECharts图表展示
- 预测到出栏日（通常300天或100kg）
- 每月一个数据点，便于追踪

### 3. 数值引擎深度推演
```markdown
### 🏗️ 数值引擎深度推演
- **基准模型**：Gompertz 生长动力学方程
- **历史匹配**：成功找到 3 头具有高度相似性的历史猪只
  - 案例 `pig_lc_001`：时序形态距离 0.123
  - 案例 `pig_lc_005`：时序形态距离 0.156
- **结论总结**：生长速率符合预期
```

**解读**:
- 时序形态距离越小，相似度越高
- 距离 < 0.5: 高度相似
- 距离 0.5-1.0: 中等相似
- 距离 > 1.0: 相似度较低

### 4. AI专家诊断
```markdown
### 🩺 AI 专家诊断与干预建议
---
### 风险评估
- 生长正常，未发现异常指标

### 干预建议
- 继续观察，保持当前饲养方案
---
*报告生成时间：2026-04-02 15:30:45*
```

**解读**:
- 基于LLM分析历史案例生成
- 包含风险评估和具体建议
- 时间戳确保报告时效性

---

## 前端集成

### Vue 3 + ECharts 示例

```vue
<template>
  <div class="growth-curve-chart">
    <div ref="chartRef" style="width: 100%; height: 400px;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

const chartRef = ref(null)

async function loadGrowthCurve(pigId) {
  // 1. 调用API获取预测数据
  const response = await axios.post('/api/v1/agent/chat/v2', {
    user_id: 'current_user',
    messages: [
      { role: 'user', content: `查询猪只${pigId}的生长曲线` }
    ]
  })
  
  // 2. 解析Markdown报告中的表格数据
  const report = response.data.reply
  const tableRegex = /\| (\d+) \| ([\d.]+) \| (.+?) \|/g
  const data = []
  let match
  
  while ((match = tableRegex.exec(report)) !== null) {
    data.push({
      month: parseInt(match[1]),
      weight: parseFloat(match[2]),
      status: match[3].trim()
    })
  }
  
  // 3. 渲染ECharts图表
  const chart = echarts.init(chartRef.value)
  chart.setOption({
    title: { text: '生长曲线预测' },
    xAxis: {
      type: 'category',
      data: data.map(d => `${d.month}月`)
    },
    yAxis: {
      type: 'value',
      name: '体重 (kg)'
    },
    series: [{
      data: data.map(d => d.weight),
      type: 'line',
      smooth: true,
      markPoint: {
        data: [
          { type: 'max', name: '最大值' },
          { 
            coord: [0, data[0].weight],
            name: '当前',
            itemStyle: { color: 'red' }
          }
        ]
      }
    }]
  })
}

onMounted(() => {
  loadGrowthCurve('PIG001')
})
</script>
```

---

## 常见问题

### Q1: 为什么预测结果不准确？

**可能原因**:
1. 历史数据不足（向量库中相似案例少）
2. 当前猪只品种与历史数据不匹配
3. 输入数据质量问题（体重、进食数据异常）

**解决方案**:
- 增加历史数据样本
- 确保品种匹配
- 验证输入数据的准确性

### Q2: 如何提高预测准确度？

**建议**:
1. 定期更新向量数据库（添加新的历史案例）
2. 使用更细粒度的数据（每周而非每月）
3. 结合环境数据（温度、湿度）进行综合分析

### Q3: 报告生成失败怎么办？

**排查步骤**:
1. 检查日志: `tail -f ai-service/logs/algorithm.log`
2. 验证输入参数格式
3. 确认向量数据库已初始化
4. 检查LLM API连接（如使用AI诊断功能）

### Q4: 如何自定义预测参数？

**修改配置**:
```python
# ai-service/pig_rag/math_engine/curve_fitter.py

# 修改标准生长模型参数
STANDARD_PARAMS = {
    "A": 135.0,   # 成年体重上限
    "b": 4.5,     # 初始偏置常数
    "c": 0.012,   # 生长速率
}

# 修改预测目标日龄
result = predict_growth_curve(
    current_day_age=90,
    current_weight_series=weights,
    top_k_matches=matches,
    target_day_age=300,  # 修改此值
    use_gompertz_fit=True
)
```

---

## 性能优化

### 1. 向量数据库缓存
```python
# 使用全局变量缓存向量库
_vectorstore: Chroma | None = None

def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = init_lifecycle_vector_db()
    return _vectorstore
```

### 2. 批量预测
```python
async def batch_predict(pig_ids: list[str]):
    tasks = [
        tool_query_pig_growth_prediction(json.dumps({"pig_id": pid}))
        for pid in pig_ids
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. 结果缓存
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_prediction(pig_id: str, current_month: int):
    return query_pig_growth_prediction(...)
```

---

## 相关文档

- [多智能体架构指南](MULTI_AGENT_GUIDE.md)
- [生长曲线修复总结](../GROWTH_CURVE_FIX_SUMMARY.md)
- [API文档](../../backend/API_DOCS.md)
- [项目README](../../README.md)

---

## 技术支持

如有问题，请查看:
1. 日志文件: `ai-service/logs/algorithm.log`
2. 测试用例: `ai-service/tests/test_growth_curve_crash_fix.py`
3. 调试页面: http://localhost:8000/static/debug.html

或联系开发团队获取支持。
