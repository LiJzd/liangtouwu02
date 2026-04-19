<script setup lang="ts">import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';

const stats = ref({
    count: '14,502',
    countChange: '+2.4%',
    efficiency: '92.5%',
    mortality: '0.5%',
    avgWeight: '2.3kg',
    feedRatio: '1.5:1',
    dailyFeed: '12.5T',
    dailyWater: '48.2m³',
    deviceOnline: '99.8%',
});

const gasChartRef = ref<HTMLElement | null>(null);
let charts: echarts.ECharts[] = [];

onMounted(async () => {
    await nextTick();
    if (gasChartRef.value) initMultiGasChart(gasChartRef.value);

    const handleResize = () => charts.forEach(c => c.resize());
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    window.removeEventListener('resize', () => charts.forEach(c => c.resize()));
    charts.forEach(c => c.dispose());
});

function initMultiGasChart(el: HTMLElement) {
    const hexToRgba = (hex: string, alpha: number) => {
        let r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    const myChart = echarts.init(el);
    charts.push(myChart);
    const hours = ['00:00', '06:00', '12:00', '18:00', '23:59'];
    
    const nh3Data = [4.2, 3.5, 6.1, 8.2, 5.0];
    const co2Data = [410, 390, 520, 680, 450];

    const option = {
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)' },
        grid: { left: 40, right: 40, bottom: 20, top: 20, containLabel: true },
        xAxis: { 
            type: 'category', 
            boundaryGap: false, 
            data: hours, 
            axisLine: { show: false }, 
            axisTick: { show: false },
            axisLabel: { fontSize: 10, fontWeight:'bold', color: '#064e3b', opacity: 0.6 }
        },
        yAxis: [
            { 
               type: 'value', 
               splitLine: { show: true, lineStyle: { type: 'solid', color:'#d1fae5'} }, 
               axisLabel: { show: false } 
            },
            { 
               type: 'value', 
               splitLine: { show: false }, 
               axisLabel: { show: false } 
            }
        ],
        series: [
            {
                name: 'NH3 氨气 (ppm)', 
                type: 'line', 
                smooth: true, 
                symbol: 'none',
                lineStyle: { width: 3, color: '#059669' },
                data: nh3Data,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: hexToRgba('#059669', 0.2) },
                        { offset: 1, color: hexToRgba('#059669', 0) }
                    ])
                }
            },
            {
                name: 'CO2 二氧化碳 (ppm)', 
                type: 'line', 
                yAxisIndex: 1,
                smooth: true, 
                symbol: 'none',
                lineStyle: { width: 2, color: '#10b981', type: 'dashed' },
                data: co2Data,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: hexToRgba('#10b981', 0.1) },
                        { offset: 1, color: hexToRgba('#10b981', 0) }
                    ])
                }
            }
        ]
    };
    
    myChart.setOption(option);
}
</script>

<template>
  <div class="pb-12 min-h-screen">
    <!-- Hero Header Section -->
    <section class="relative w-full h-[180px] flex items-center justify-center overflow-hidden border-b border-emerald-200 bg-emerald-200/30">
      <div class="absolute inset-0 z-0 flex justify-center items-center opacity-30 pointer-events-none">
        <div class="w-[600px] h-[600px] bg-emerald-300 blur-[100px] rounded-full"></div>
      </div>
      <div class="relative z-10 flex flex-col items-center px-4 text-center mt-6">
        <span class="text-primary font-headline font-bold tracking-[0.4em] text-[10px] mb-2 uppercase">COMMAND CENTER</span>
        <h1 class="text-3xl md:text-4xl font-headline font-bold text-emerald-950 tracking-tight">两头乌智能养殖概览</h1>
      </div>
    </section>

    <!-- Content wrap -->
    <div class="max-w-7xl mx-auto space-y-8 px-6 pt-8">
      
      <!-- Dashboard Sub-Header -->
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <span class="text-primary font-headline font-bold tracking-widest text-[10px] uppercase">指挥中心面板</span>
          <h2 class="text-xl font-headline font-bold text-emerald-950 mt-1">关键性能指标监测</h2>
        </div>
        <div class="flex items-center gap-3 px-4 py-1.5 bg-white/90 backdrop-blur-sm rounded-full border border-emerald-200 shadow-sm">
          <div class="w-2.5 h-2.5 rounded-full bg-secondary pulse-indicator"></div>
          <span class="text-xs font-bold text-emerald-900">实时数据流: <span class="text-emerald-600">同步稳定</span></span>
        </div>
      </div>

      <!-- Hero Metrics -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main Metric 1 -->
        <div class="lg:col-span-2 bg-white/95 p-8 rounded-xl relative overflow-hidden flex flex-col justify-between h-56 border border-emerald-200 shadow-sm hover:shadow-md transition-all">
          <div class="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
            <svg viewBox="0 0 24 24" class="w-[100px] h-[100px] text-emerald-900" fill="currentColor">
              <path d="M12,4C6.48,4,2,7.58,2,12s4.48,8,10,8s10-3.58,10-8S17.52,4,12,4z M8.5,14c-0.83,0-1.5-0.67-1.5-1.5S7.67,11,8.5,11 S10,11.67,10,12.5S9.33,14,8.5,14z M15.5,14c-0.83,0-1.5-0.67-1.5-1.5s0.67-1.5,1.5-1.5s1.5,0.67,1.5,1.5S16.33,14,15.5,14z"/>
            </svg>
          </div>
          <div class="flex justify-between items-start">
            <div>
              <p class="text-emerald-900 font-bold text-xs uppercase tracking-wider">全场实时总数</p>
              <h3 class="text-5xl font-headline font-bold text-emerald-950 tracking-tighter mt-2">{{ stats.count }} <span class="text-lg font-normal text-on-surface-variant">头</span></h3>
            </div>
            <div class="bg-emerald-100 px-3 py-1 rounded-full flex items-center gap-1 border border-emerald-200">
              <span class="material-symbols-outlined text-secondary text-sm">trending_up</span>
              <span class="text-secondary font-bold text-sm">{{ stats.countChange }}</span>
            </div>
          </div>
          <div class="flex items-end gap-2 text-xs text-on-surface-variant">
            <span class="text-primary font-bold">482</span> <span class="font-semibold text-emerald-900/70">本周新增存栏</span>
          </div>
        </div>

        <!-- Main Metric 2 -->
        <div class="bg-white/95 p-8 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between h-56 hover:shadow-md transition-all">
          <div>
            <p class="text-emerald-900 font-bold text-xs uppercase tracking-wider">核心繁育效率</p>
            <h3 class="text-5xl font-headline font-bold text-secondary tracking-tighter mt-2">{{ stats.efficiency }}</h3>
          </div>
          <div class="space-y-4">
            <div class="w-full h-2.5 bg-emerald-100 rounded-full overflow-hidden">
              <div class="w-[92.5%] h-full bg-secondary"></div>
            </div>
            <p class="text-[10px] text-emerald-900 font-bold">高出年度目标值 <span class="text-emerald-950">4.1%</span></p>
          </div>
        </div>
      </div>

      <!-- Analytics & Surveillance -->
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <!-- Gas Chart -->
        <div class="lg:col-span-3 bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col h-[360px]">
          <div class="flex justify-between items-center mb-4 shrink-0">
            <div>
              <h4 class="font-headline font-bold text-lg text-emerald-950">微环境趋势纵览</h4>
              <p class="text-[10px] font-bold text-emerald-800/80 uppercase tracking-wider">多维气体指标监测 — 24小时演变走势</p>
            </div>
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-secondary"></span>
                <span class="text-[9px] font-bold text-emerald-900 uppercase">NH3 氨气</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-white border-2 border-secondary"></span>
                <span class="text-[9px] font-bold text-emerald-900 uppercase">CO2 二氧化碳</span>
              </div>
            </div>
          </div>
          <div ref="gasChartRef" class="flex-1 w-full min-h-0 relative"></div>
        </div>

        <!-- Video System -->
        <div class="lg:col-span-2 bg-white rounded-xl border border-emerald-200 overflow-hidden shadow-sm group h-[360px]">
          <div class="relative h-full w-full">
            <video autoplay loop muted playsinline class="w-full h-full object-cover grayscale brightness-90 group-hover:brightness-100 transition-all duration-700" src="https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=smart%20pig%20farm%20monitoring%20video%20surveillance&image_size=landscape_16_9"></video>
            <div class="absolute inset-0 bg-emerald-900/15 mix-blend-multiply pointer-events-none"></div>
            <div class="absolute inset-0 p-6 flex flex-col justify-between">
              <div class="flex justify-between items-start">
                <div class="bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-lg text-[9px] font-bold text-emerald-950 uppercase tracking-widest flex items-center gap-2 border border-emerald-200">
                  <span class="w-1.5 h-1.5 rounded-full bg-red-600 animate-pulse"></span>
                  04栋保育舍 • 实时
                </div>
                <span class="material-symbols-outlined text-emerald-950/60 object-contain">videocam</span>
              </div>
              <div class="bg-white/95 backdrop-blur-md p-4 rounded-lg border border-emerald-200 shadow-lg">
                <div class="flex justify-between items-center text-[10px] text-emerald-950 font-bold mb-2">
                  <span>温度实时偏移分析</span>
                  <span class="text-secondary font-bold">+0.2°C</span>
                </div>
                <div class="h-8 w-full">
                  <svg class="w-full h-full" viewBox="0 0 100 20" preserveAspectRatio="none">
                    <polyline fill="none" points="0,15 10,12 20,18 30,5 40,10 50,2 60,15 70,8 80,12 90,5 100,10" stroke="#059669" stroke-width="2"></polyline>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Secondary Metrics -->
      <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div class="lg:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-max">
          <!-- Rate -->
          <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col gap-3 hover:-translate-y-1 transition duration-300">
            <div class="flex items-center justify-between">
              <span class="material-symbols-outlined text-primary text-xl">skull</span>
              <span class="text-[9px] font-bold bg-emerald-100 text-emerald-900 px-2 py-0.5 rounded-full border border-emerald-200">目标 0.8%</span>
            </div>
            <div>
               <p class="text-[10px] text-emerald-900 font-bold uppercase tracking-wider">当日死亡率</p>
               <p class="text-2xl font-headline font-bold text-emerald-950">{{ stats.mortality }}</p>
            </div>
            <div class="h-10 w-full mt-1">
               <svg class="w-full h-full opacity-60 chart-line" viewBox="0 0 100 30" preserveAspectRatio="none">
                 <path d="M 0,25 Q 10,23.5 20,22 T 40,28 T 60,15 T 80,18 T 100,20" fill="none" stroke="#059669" stroke-linecap="round" stroke-width="3"></path>
               </svg>
            </div>
          </div>

          <!-- Weight -->
          <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col gap-3 hover:-translate-y-1 transition duration-300">
            <div class="flex items-center justify-between">
              <span class="material-symbols-outlined text-primary text-xl">weight</span>
              <span class="text-[9px] font-bold text-secondary flex items-center"><span class="material-symbols-outlined text-xs">arrow_upward</span>5%</span>
            </div>
            <div>
               <p class="text-[10px] text-emerald-900 font-bold uppercase tracking-wider">场均体重</p>
               <p class="text-2xl font-headline font-bold text-emerald-950">{{ stats.avgWeight }}</p>
            </div>
            <div class="h-10 w-full mt-1">
               <svg class="w-full h-full opacity-60 chart-line" viewBox="0 0 100 30" preserveAspectRatio="none">
                 <path d="M 0,28 Q 10,26.5 20,25 T 40,20 T 60,15 T 80,10 T 100,5" fill="none" stroke="#059669" stroke-linecap="round" stroke-width="3"></path>
               </svg>
            </div>
          </div>

          <!-- Feed -->
          <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col gap-3 hover:-translate-y-1 transition duration-300">
            <div class="flex items-center justify-between">
              <span class="material-symbols-outlined text-primary text-xl">restaurant</span>
              <span class="text-[9px] font-bold text-emerald-900/60 uppercase">稳定运行</span>
            </div>
            <div>
               <p class="text-[10px] text-emerald-900 font-bold uppercase tracking-wider">全周料肉比</p>
               <p class="text-2xl font-headline font-bold text-emerald-950">{{ stats.feedRatio }}</p>
            </div>
            <div class="h-10 w-full mt-1">
               <svg class="w-full h-full opacity-60 chart-line" viewBox="0 0 100 30" preserveAspectRatio="none">
                 <path d="M 0,15 Q 10,15.5 20,16 T 40,14 T 60,15 T 80,16 T 100,15" fill="none" stroke="#059669" stroke-linecap="round" stroke-width="3"></path>
               </svg>
            </div>
          </div>

          <!-- Daily Feed -->
          <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col gap-3 hover:-translate-y-1 transition duration-300">
            <div class="flex items-center justify-between">
              <span class="material-symbols-outlined text-indigo-500 text-xl">conveyor_belt</span>
              <span class="text-[9px] font-bold bg-indigo-100 text-indigo-900 px-2 py-0.5 rounded-full border border-indigo-200">标准区间</span>
            </div>
            <div>
               <p class="text-[10px] text-emerald-900 font-bold uppercase tracking-wider">场均日供料总计</p>
               <p class="text-2xl font-headline font-bold text-emerald-950">{{ stats.dailyFeed }}</p>
            </div>
            <div class="h-10 w-full mt-1">
               <svg class="w-full h-full opacity-60 chart-line" viewBox="0 0 100 30" preserveAspectRatio="none">
                 <path d="M 0,22 Q 10,23 20,21 T 40,25 T 60,20 T 80,18 T 100,22" fill="none" stroke="#6366f1" stroke-linecap="round" stroke-width="3"></path>
               </svg>
            </div>
          </div>
          
          <!-- Daily Water -->
          <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col gap-3 hover:-translate-y-1 transition duration-300">
            <div class="flex items-center justify-between">
              <span class="material-symbols-outlined text-cyan-500 text-xl">water_drop</span>
              <span class="text-[9px] font-bold text-cyan-600 flex items-center"><span class="material-symbols-outlined text-xs">arrow_downward</span>1.2%</span>
            </div>
            <div>
               <p class="text-[10px] text-emerald-900 font-bold uppercase tracking-wider">每日饮水流转</p>
               <p class="text-2xl font-headline font-bold text-emerald-950">{{ stats.dailyWater }}</p>
            </div>
            <div class="h-10 w-full mt-1">
               <svg class="w-full h-full opacity-60 chart-line" viewBox="0 0 100 30" preserveAspectRatio="none">
                 <path d="M 0,10 Q 10,12 20,8 T 40,15 T 60,12 T 80,10 T 100,12" fill="none" stroke="#06b6d4" stroke-linecap="round" stroke-width="3"></path>
               </svg>
            </div>
          </div>

          <!-- Device Status -->
          <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col gap-3 hover:-translate-y-1 transition duration-300">
            <div class="flex items-center justify-between">
              <span class="material-symbols-outlined text-amber-500 text-xl">router</span>
              <span class="text-[9px] font-bold bg-amber-100 text-amber-900 px-2 py-0.5 rounded-full border border-amber-200">9 离线异常</span>
            </div>
            <div>
               <p class="text-[10px] text-emerald-900 font-bold uppercase tracking-wider">核心设备在线率</p>
               <p class="text-2xl font-headline font-bold text-emerald-950">{{ stats.deviceOnline }}</p>
            </div>
            <div class="h-10 w-full mt-1">
               <svg class="w-full h-full opacity-60 chart-line" viewBox="0 0 100 30" preserveAspectRatio="none">
                 <path d="M 0,2 Q 10,5 20,4 T 40,3 T 60,8 T 80,15 T 100,2" fill="none" stroke="#f59e0b" stroke-linecap="round" stroke-width="3"></path>
               </svg>
            </div>
          </div>
        </div>

        <!-- Alerts -->
        <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm h-full flex flex-col">
          <div class="flex justify-between items-center mb-6">
            <h4 class="font-headline font-bold text-emerald-950">实时告警</h4>
            <span class="text-[9px] font-bold text-emerald-900 bg-emerald-100 px-2 py-1 rounded-full border border-emerald-200">3 条待办</span>
          </div>
          <div class="space-y-4 flex-1">
            <div class="flex gap-4 p-3 rounded-lg bg-red-50 border-l-4 border-red-500 shadow-sm hover:translate-x-1 transition cursor-pointer">
              <span class="material-symbols-outlined text-red-600 text-xl">warning</span>
              <div>
                <p class="text-[11px] font-bold text-emerald-950">水流异常</p>
                <p class="text-[9px] text-emerald-900 font-semibold mt-1">02扇区 - 管道压力突降</p>
                <p class="text-[8px] text-emerald-900/50 font-bold mt-2">2分钟前</p>
              </div>
            </div>
            
            <div class="flex gap-4 p-3 rounded-lg bg-emerald-50 border-l-4 border-emerald-600 shadow-sm hover:translate-x-1 transition cursor-pointer">
              <span class="material-symbols-outlined text-emerald-600 text-xl">info</span>
              <div>
                <p class="text-[11px] font-bold text-emerald-950">自动投喂计划</p>
                <p class="text-[9px] text-emerald-900 font-semibold mt-1">04循环已在所有区域启动</p>
                <p class="text-[8px] text-emerald-900/50 font-bold mt-2">15分钟前</p>
              </div>
            </div>
            
            <div class="flex gap-4 p-3 rounded-lg bg-blue-50 border-l-4 border-blue-500 shadow-sm hover:translate-x-1 transition cursor-pointer">
              <span class="material-symbols-outlined text-blue-600 text-xl">check_circle</span>
              <div>
                <p class="text-[11px] font-bold text-emerald-950">健康巡检完成</p>
                <p class="text-[9px] text-emerald-900 font-semibold mt-1">07栋: 0 异常检出</p>
                <p class="text-[8px] text-emerald-900/50 font-bold mt-2">1小时前</p>
              </div>
            </div>
          </div>
          <button class="w-full mt-6 py-2.5 text-[10px] font-bold text-emerald-900 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors uppercase tracking-widest">
            查看完整历史
          </button>
        </div>
      </div>
    </div>
  </div>
</template>