<script setup lang="ts">
/**
 * 仪表盘 (Dashboard) 视图组件
 * =====================================
 * 本组件是养殖场系统的“数字大脑”首页，负责展示全场的核心实时统计指标。
 * 
 * 界面风格：
 * - 采用硬朗的方正无衬线设计，强调工业化与专业感。
 * - 使用大字号数字展现核心数值，确保在大屏上清晰可见。
 */
import { ref, onMounted } from 'vue';
// 引入 Lucide 图标库，增加界面语义化
import { Thermometer, Activity, AlertTriangle, Package } from 'lucide-vue-next';

// 核心统计状态
const stats = ref<any>({
    stockCount: 1580,   // 总存栏数
    healthRate: 99.2,   // 健康率百分比
    averageTemp: 38.4,  // 全场平均体温
    alertCount: 7,      // 今日新增报警数
});

onMounted(() => {
  // 当前演示版本采用模拟数据，生产环境此处应调用 apiService.getDashboardStats()
});
</script>

<template>
  <div class="h-full flex flex-col space-y-6">
    <!-- 统计卡片网格 -->
    <div class="grid grid-cols-2 gap-6 flex-1 min-h-0">
      
      <!-- 1. 存栏数卡片 -->
      <div class="bg-white p-10 rounded-none border border-slate-300 flex items-center justify-between transition-all hover:border-slate-500 hover:shadow-lg group">
        <div>
          <p class="text-sm font-bold text-slate-500 mb-2 uppercase tracking-widest">存栏总数</p>
          <div class="flex items-baseline mt-4">
            <span class="text-7xl font-mono font-bold text-slate-900 tracking-tighter">{{ stats.stockCount }}</span>
            <span class="ml-4 text-xl font-mono text-slate-500 uppercase">Head</span>
          </div>
        </div>
        <div class="p-8 rounded-none bg-indigo-600 transition-transform group-hover:scale-105">
          <Package class="w-12 h-12 text-white" />
        </div>
      </div>

      <!-- 2. 健康率卡片 -->
      <div class="bg-white p-10 rounded-none border border-slate-300 flex items-center justify-between transition-all hover:border-slate-500 hover:shadow-lg group">
        <div>
          <p class="text-sm font-bold text-slate-500 mb-2 uppercase tracking-widest">实时健康率</p>
          <div class="flex items-baseline mt-4">
            <span class="text-7xl font-mono font-bold text-slate-900 tracking-tighter">{{ stats.healthRate }}</span>
            <span class="ml-4 text-xl font-mono text-slate-500">%</span>
          </div>
        </div>
        <div class="p-8 rounded-none bg-emerald-600 transition-transform group-hover:scale-105">
          <Activity class="w-12 h-12 text-white" />
        </div>
      </div>

      <!-- 3. 平均温度卡片 -->
      <div class="bg-white p-10 rounded-none border border-slate-300 flex items-center justify-between transition-all hover:border-slate-500 hover:shadow-lg group">
        <div>
          <p class="text-sm font-bold text-slate-500 mb-2 uppercase tracking-widest">全场平均体温</p>
          <div class="flex items-baseline mt-4">
            <span class="text-7xl font-mono font-bold text-slate-900 tracking-tighter">{{ stats.averageTemp }}</span>
            <span class="ml-4 text-xl font-mono text-slate-500">°C</span>
          </div>
        </div>
        <div class="p-8 rounded-none bg-blue-600 transition-transform group-hover:scale-105">
          <Thermometer class="w-12 h-12 text-white" />
        </div>
      </div>

      <!-- 4. 今日报警卡片 -->
      <div class="bg-white p-10 rounded-none border border-slate-300 flex items-center justify-between transition-all hover:border-slate-500 hover:shadow-lg group">
        <div>
          <p class="text-sm font-bold text-slate-500 mb-2 uppercase tracking-widest">今日处理报警</p>
          <div class="flex items-baseline mt-4">
            <span class="text-7xl font-mono font-bold text-slate-900 tracking-tighter">{{ stats.alertCount }}</span>
            <span class="ml-4 text-xl font-mono text-slate-500">Count</span>
          </div>
        </div>
        <div class="p-8 rounded-none bg-red-600 transition-transform group-hover:scale-105">
          <AlertTriangle class="w-12 h-12 text-white" />
        </div>
      </div>

    </div>
  </div>
</template>
