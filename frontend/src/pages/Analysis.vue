<script setup lang="ts">
/**
 * 智能分析 (Analysis) 视图组件
 * =====================================
 * 本组件负责多维度的养殖场现状评估，包含两个核心逻辑板块：
 * 
 * 1. 环境大数据看板 (左侧)：
 *    - 支持两种模式切换：全区域对比 bar 图 vs 特定区域 24h 趋势 line 图。
 *    - 核心逻辑基于 vue-router 的 query 参数 `area` 动态触发数据重载。
 * 
 * 2. 异常生猪风险排行 (右侧)：
 *    - 实时同步后端计算的“异常评分”列表。
 *    - 采用“排行榜”视觉设计，突出优先级最高（风险最大）的个体。
 */

import { ref, onMounted, watch, computed, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import * as echarts from 'echarts';
import { Trophy, TrendingUp, AlertCircle, BarChart2 } from 'lucide-vue-next';
import { apiService } from '../api';
import { cn } from '../utils';

// --- 路由与状态 ---
const route = useRoute();
const chartContainer = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;

const trends = ref<any[]>([]);       // 时序趋势数据
const areaStats = ref<any[]>([]);    // 区域聚合统计
const abnormalPigs = ref<any[]>([]); // 风险排行数据
const loading = ref(true);

/** 计算属性：从 URL 获取当前聚焦的区域名称 */
const filterArea = computed(() => route.query.area as string | undefined);

/**
 * 核心数据获取与渲染逻辑
 * 根据 URL 状态决定是请求“区域概览”还是“特定趋势”。
 */
const fetchAndRender = async () => {
  loading.value = true;
  try {
    const promises = [
      apiService.getAbnormalPigs(), // 同时加载风险排行
      // 动态分支：有区域参数则查趋势，无则查概览
      filterArea.value ? apiService.getEnvironmentTrends() : apiService.getAreaStats()
    ];

    const [pigsRes, chartRes] = await Promise.all(promises);
    abnormalPigs.value = pigsRes.data;
    
    // 数据分类存储
    if (filterArea.value) {
      trends.value = chartRes.data;
      areaStats.value = [];
    } else {
      areaStats.value = chartRes.data;
      trends.value = [];
    }
  } finally {
    loading.value = false;
    // 确保 DOM 渲染后再初始化图表（使用 setTimeout 0 放入宏任务队列）
    setTimeout(initChart, 0); 
  }
};

/** ECharts 初始化与配置切换逻辑 */
const initChart = () => {
    if (!chartContainer.value) return;
    if (!chartInstance) {
        chartInstance = echarts.init(chartContainer.value);
    }
    
    let option: any = {};

    // 模式 1: 趋势图 (Line Chart)
    if (filterArea.value) {
        option = {
            grid: { top: 10, right: 30, left: 40, bottom: 20 },
            xAxis: {
                type: 'category',
                boundaryGap: false,
                data: trends.value.map(item => item.time),
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'monospace' }
            },
            yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'monospace' },
                splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                borderColor: '#cbd5e1',
                textStyle: { fontFamily: 'monospace', fontSize: 12 },
                borderRadius: 0,
                formatter: (params: any) => {
                   return `<div class="uppercase">${params[0].name}</div>
                           <div style="color:${params[0].color}">温度: ${params[0].value}°C</div>`
                }
            },
            series: [{
                data: trends.value.map(item => item.temperature),
                type: 'line',
                smooth: true,
                symbol: 'none',
                lineStyle: { color: '#2563eb', width: 2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(37, 99, 235, 0.1)' },
                        { offset: 1, color: 'rgba(37, 99, 235, 0)' }
                    ])
                }
            }]
        };
    } 
    // 模式 2: 对比图 (Bar Chart)
    else {
        option = {
            grid: { top: 10, right: 30, left: 40, bottom: 20 },
            xAxis: {
                type: 'category',
                data: areaStats.value.map((item: any) => item.name),
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#64748b', fontSize: 12 }
            },
            yAxis: {
                type: 'value',
                min: 35, // 设定猪只体温敏感区间
                max: 40,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { color: '#64748b', fontSize: 10, fontFamily: 'monospace' },
                splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } }
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                axisPointer: { type: 'shadow' }
            },
            series: [{
                data: areaStats.value.map((item: any) => item.temperature),
                type: 'bar',
                barWidth: 40,
                itemStyle: { 
                    color: '#2563eb',
                    borderRadius: [2, 2, 0, 0]
                }
            }]
        };
    }
    
    chartInstance.setOption(option);
}

// --- 组件生命周期 ---
onMounted(() => {
    fetchAndRender();
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    chartInstance?.dispose();
});

const handleResize = () => chartInstance?.resize();

/** 深度监听：URL 参数变化时，强制重置图表并刷新数据 */
watch(() => route.query.area, () => {
    chartInstance?.dispose(); 
    chartInstance = null;
    fetchAndRender();
});
</script>

<template>
  <div v-if="loading" class="p-10 text-center text-slate-500 font-mono uppercase">数据链路同步中...</div>
  <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-8rem)]">
      
      <!-- 左侧：环境维度分析栏 -->
      <div class="lg:col-span-2 bg-white rounded-none border border-slate-300 p-6 flex flex-col">
        <div class="flex items-center justify-between mb-6 border-b border-slate-100 pb-4">
          <h2 class="text-sm font-bold text-slate-800 flex items-center uppercase tracking-widest">
            <!-- 动态标题 -->
            <template v-if="filterArea">
                <TrendingUp class="w-4 h-4 mr-2 text-blue-600" />
                24小时环境温度趋势 <span class="ml-2 text-slate-500 font-normal normal-case">- {{ filterArea }}</span>
            </template>
            <template v-else>
                <BarChart2 class="w-4 h-4 mr-2 text-blue-600" />
                区域温度对比概览 (实时)
            </template>
          </h2>
          <div class="flex items-center space-x-2 text-xs uppercase font-bold tracking-wide">
            <span class="flex items-center"><span class="w-2 h-2 bg-blue-600 rounded-none mr-2"></span> 环境温度传感器</span>
          </div>
        </div>

        <div class="flex-1 min-h-0 relative">
             <div ref="chartContainer" class="w-full h-full"></div>
        </div>
      </div>

      <!-- 右侧：风险生猪领奖台 (Leaderboard) -->
      <div class="bg-white rounded-none border border-slate-300 p-0 flex flex-col">
        <div class="p-6 border-b border-slate-300 bg-slate-50">
          <h2 class="text-sm font-bold text-slate-800 flex items-center uppercase tracking-widest">
            <Trophy class="w-4 h-4 mr-2 text-blue-600" />
            AI 预警生猪排行 (Top N)
          </h2>
        </div>

        <div class="flex-1 overflow-y-auto p-0">
            <!-- 每条记录基于 index 展示不同的视觉权重 -->
            <div v-for="(pig, index) in abnormalPigs" :key="pig.id" class="flex items-center p-4 border-b border-slate-100 hover:bg-slate-50 transition-colors group">
              <div :class="cn(
                'w-8 h-8 flex items-center justify-center font-bold font-mono mr-4 border text-sm',
                index === 0 ? 'bg-blue-50 text-blue-700 border-blue-200' :
                  index === 1 ? 'bg-slate-100 text-slate-600 border-slate-300' :
                    index === 2 ? 'bg-slate-50 text-slate-500 border-slate-200' : 'bg-white text-slate-400 border-slate-200'
              )">
                {{ index + 1 }}
              </div>
              <div class="flex-1">
                <div class="flex justify-between items-center mb-1">
                  <span class="font-bold text-slate-700 font-mono text-sm tracking-tight">{{ pig.id }}</span>
                  <span class="text-[10px] font-mono bg-slate-100 px-2 py-0.5 border border-slate-200 text-slate-600 uppercase">风险权重: {{ pig.score }}</span>
                </div>
                <div class="flex items-center text-xs text-red-600 font-medium uppercase tracking-wide">
                  <AlertCircle class="w-3 h-3 mr-1" />
                  研判标记: {{ pig.issue }}
                </div>
              </div>
            </div>
        </div>
      </div>
  </div>
</template>
