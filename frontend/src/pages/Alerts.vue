<script setup lang="ts">
/**
 * 预警中心 (Alerts) 视图组件
 * =====================================
 * 本组件是系统的事件管理中心，负责展示实时拦截到的所有生猪异常协议。
 * 
 * 核心功能：
 * 1. 组合筛选：支持按 ID、风险等级（Critical/High/etc.）及所属区域进行多维度联动过滤。
 * 2. 状态统计：顶部统计栏实时反馈当前全场各类风险事件的数量占比。
 * 3. 动态视觉反馈：基于风险评分应用不同的颜色方案和图标，引导管理人员优先处理“危急”事件。
 */

import { reactive, computed } from 'vue';
import { Search, AlertOctagon, Filter, RefreshCcw, Download, Info } from 'lucide-vue-next';
import { cn } from '../utils';

// --- 常量定义 ---
const RISK_LEVELS = ['全部', 'Low', 'Medium', 'High', 'Critical'];
const AREAS = ['全部', '猪舍A', '猪舍B', '猪舍C', '隔离区'];

// --- 预警数据源 (Mock 演示数据) ---
const allAlerts = [
    { id: 1, pigId: 'PIG-001', area: '猪舍A', type: '异常发热', risk: 'High', timestamp: '2026-03-12 10:00' },
    { id: 2, pigId: 'PIG-023', area: '猪舍B', type: '活动力下降', risk: 'Medium', timestamp: '2026-03-12 09:45' },
    { id: 3, pigId: 'PIG-105', area: '猪舍A', type: '攻击行为', risk: 'Critical', timestamp: '2026-03-12 09:30' },
    { id: 4, pigId: 'PIG-332', area: '猪舍C', type: '设备故障', risk: 'Low', timestamp: '2026-03-12 08:15' },
    { id: 5, pigId: 'PIG-088', area: '隔离区', type: '体温偏高', risk: 'High', timestamp: '2026-03-12 07:45' },
    { id: 6, pigId: 'PIG-122', area: '猪舍B', type: '进食异常', risk: 'Medium', timestamp: '2026-03-12 06:30' },
    { id: 7, pigId: 'PIG-045', area: '猪舍A', type: '呼吸急促', risk: 'Critical', timestamp: '2026-03-12 05:20' },
    { id: 8, pigId: 'PIG-201', area: '猪舍C', type: '持续低温', risk: 'Low', timestamp: '2026-03-11 23:45' },
    { id: 9, pigId: 'PIG-012', area: '猪舍B', type: '离群行为', risk: 'Medium', timestamp: '2026-03-11 22:15' },
    { id: 10, pigId: 'PIG-007', area: '隔离区', type: '疑似口蹄疫', risk: 'Critical', timestamp: '2026-03-11 21:00' },
    { id: 11, pigId: 'PIG-155', area: '猪舍A', type: '伤残预警', risk: 'High', timestamp: '2026-03-11 20:30' },
    { id: 12, pigId: 'PIG-302', area: '猪舍C', type: '传感器离线', risk: 'Low', timestamp: '2026-03-11 19:45' },
];

// --- 响应式过滤状态 ---
const filters = reactive({
  search: '',
  risk: '全部',
  area: '全部'
});

/** 计算属性：执行组合过滤逻辑 */
const filteredAlerts = computed(() => {
  return allAlerts.filter(alert => {
    const matchSearch = alert.pigId.toLowerCase().includes(filters.search.toLowerCase()) || 
                      alert.type.toLowerCase().includes(filters.search.toLowerCase());
    const matchRisk = filters.risk === '全部' || alert.risk === filters.risk;
    const matchArea = filters.area === '全部' || alert.area === filters.area;
    return matchSearch && matchRisk && matchArea;
  });
});

/** 汇总统计逻辑 */
const summaryStats = computed(() => {
  return {
    total: allAlerts.length,
    critical: allAlerts.filter(a => a.risk === 'Critical').length,
    high: allAlerts.filter(a => a.risk === 'High').length,
    medium: allAlerts.filter(a => a.risk === 'Medium').length,
    low: allAlerts.filter(a => a.risk === 'Low').length,
  };
});

/** 标签翻译逻辑 */
const getRiskLabel = (risk: string) => {
  switch (risk) {
    case 'Critical': return '危急';
    case 'High': return '高风险';
    case 'Medium': return '中风险';
    case 'Low': return '低风险';
    default: return risk;
  }
};
</script>

<template>
  <div class="space-y-6 flex flex-col h-full overflow-hidden">
    
    <!-- 顶部：分类汇总卡片 (汇总当前全场态势) -->
    <div class="grid grid-cols-5 gap-4">
      <div class="bg-white p-4 border border-slate-300 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">记录总数</span>
        <span class="text-3xl font-mono font-bold text-slate-900 mt-2">{{ summaryStats.total }}</span>
      </div>
      <div class="bg-red-50 p-4 border border-red-200 border-l-4 border-l-red-600 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-red-600 uppercase tracking-widest">危急事项</span>
        <span class="text-3xl font-mono font-bold text-red-700 mt-2">{{ summaryStats.critical }}</span>
      </div>
      <div class="bg-orange-50 p-4 border border-orange-200 border-l-4 border-l-orange-600 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-orange-600 uppercase tracking-widest">高风险</span>
        <span class="text-3xl font-mono font-bold text-orange-700 mt-2">{{ summaryStats.high }}</span>
      </div>
      <div class="bg-yellow-50 p-4 border border-yellow-200 border-l-4 border-l-yellow-600 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-yellow-600 uppercase tracking-widest">中风险</span>
        <span class="text-3xl font-mono font-bold text-yellow-700 mt-2">{{ summaryStats.medium }}</span>
      </div>
      <div class="bg-blue-50 p-4 border border-blue-200 border-l-4 border-l-blue-600 flex flex-col justify-between text-blue-700">
        <span class="text-[10px] font-bold text-blue-600 uppercase tracking-widest">低风险</span>
        <span class="text-3xl font-mono font-bold text-blue-800 mt-2">{{ summaryStats.low }}</span>
      </div>
    </div>

    <!-- 主表格：预警控制台 -->
    <div class="bg-white border border-slate-300 flex flex-col flex-1 min-h-0 bg-[linear-gradient(rgba(0,0,0,0.01)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.01)_1px,transparent_1px)] bg-[size:32px_32px]">
      
      <!-- 列表头部：组合查询工作区 -->
      <div class="p-4 border-b border-slate-300 flex items-center justify-between gap-4 bg-white/80 backdrop-blur-sm sticky top-0 z-20">
        <div class="flex items-center space-x-3 flex-1">
          <!-- ID 搜索 -->
          <div class="relative w-64 group">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 group-focus-within:text-blue-600" />
            <input
              type="text"
              placeholder="搜索猪只 ID 或事件..."
              class="w-full pl-9 pr-4 py-1.5 border border-slate-300 focus:outline-none focus:border-blue-600 font-mono text-xs placeholder-slate-400 bg-slate-50/50"
              v-model="filters.search"
            />
          </div>

          <div class="h-6 w-px bg-slate-300"></div>

          <!-- 区域过滤 -->
          <div class="flex items-center space-x-2">
            <Filter class="w-3.5 h-3.5 text-slate-500" />
            <select
              class="pl-2 pr-8 py-1.5 border border-slate-300 bg-slate-50/50 font-mono text-[11px] font-bold appearance-none cursor-pointer"
              v-model="filters.area"
            >
              <option v-for="area in AREAS" :key="area" :value="area">{{ area === '全部' ? '全场区域' : area }}</option>
            </select>
          </div>

          <!-- 风险等级切换标签 -->
          <div class="flex bg-slate-100 border border-slate-300 p-0.5">
             <button
                v-for="level in RISK_LEVELS"
                :key="level"
                @click="filters.risk = level"
                :class="cn(
                  'px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-all',
                  filters.risk === level
                    ? 'bg-white text-blue-700 shadow-sm border border-slate-200'
                    : 'text-slate-500 hover:text-slate-900 border border-transparent'
                )"
              >
                {{ level }}
              </button>
          </div>
        </div>

        <!-- 辅助操作 -->
        <div class="flex items-center space-x-2">
          <button class="p-2 hover:bg-slate-100 border border-slate-300 text-slate-600" title="刷新"><RefreshCcw class="w-4 h-4" /></button>
          <button class="p-2 hover:bg-slate-100 border border-slate-300 text-slate-600" title="导出日志"><Download class="w-4 h-4" /></button>
        </div>
      </div>

      <!-- 数据主体：异常协议列表 -->
      <div class="flex-1 overflow-auto">
        <table class="w-full text-left border-collapse min-w-[800px]">
          <thead class="bg-slate-50 sticky top-0 z-10 text-slate-500 border-b border-slate-300">
            <tr>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">协议索引</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">关键目标</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">地理坐标</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">触发详情</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">风险等级</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em]">溯源时间</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 font-mono">
            <tr v-if="filteredAlerts.length === 0"><td colspan="6" class="p-16 text-center text-slate-400 text-xs font-bold uppercase tracking-widest">NO_PROTOCOL_MATCHED</td></tr>
            <tr v-for="alert in filteredAlerts" :key="alert.id" class="hover:bg-slate-50 transition-colors cursor-pointer">
              <td class="px-6 py-4 text-[11px] text-slate-400 border-r border-slate-100 italic">#{{ String(alert.id).padStart(4, '0') }}</td>
              <td class="px-6 py-4 border-r border-slate-100 font-bold text-slate-900 text-sm tracking-tighter">
                <div class="flex items-center"><span class="w-1.5 h-1.5 bg-blue-600 mr-2"></span>{{ alert.pigId }}</div>
              </td>
              <td class="px-6 py-4 text-slate-600 border-r border-slate-100 text-[11px] font-bold uppercase">{{ alert.area }}</td>
              <td class="px-6 py-4 border-r border-slate-100 text-xs font-bold text-slate-800 tracking-tight">{{ alert.type }}</td>
              <td class="px-6 py-4 border-r border-slate-100 text-xs font-bold text-slate-800 tracking-tight font-mono">
                 <div :class="cn(
                  'inline-flex items-center px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.1em] border-l-4 shadow-sm',
                  alert.risk === 'Critical' ? 'bg-red-950 text-red-100 border-l-red-500' :
                    alert.risk === 'High' ? 'bg-orange-900/10 text-orange-700 border-l-orange-500' :
                      alert.risk === 'Medium' ? 'bg-yellow-900/10 text-yellow-700 border-l-yellow-500' :
                        'bg-blue-900/10 text-blue-700 border-l-blue-500'
                )">
                  <AlertOctagon v-if="alert.risk === 'Critical'" class="w-2.5 h-2.5 mr-1.5" />
                  {{ getRiskLabel(alert.risk) }}
                </div>
              </td>
              <td class="px-6 py-4 text-slate-500 text-[10px] tabular-nums">{{ alert.timestamp }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 底栏：自检反馈 -->
      <div class="px-4 py-2 border-t border-slate-300 bg-slate-50 flex items-center justify-between">
          <div class="flex items-center text-[9px] text-slate-400 font-bold uppercase tracking-widest"><Info class="w-3 h-3 mr-2" /> 边缘感知集群工作正常</div>
          <div class="text-[9px] text-slate-400 font-mono">TOTAL: {{ filteredAlerts.length }} PROTOCOLS</div>
      </div>
    </div>
  </div>
</template>
