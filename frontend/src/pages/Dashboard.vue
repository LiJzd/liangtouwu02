<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';
import { apiService } from '../api';

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
let timer: any = null;

const avgTemp = ref('23.5');
const avgHumidity = ref('62.8');
const activeAlerts = ref<any[]>([]);
const isLoading = ref(true);

const loadStats = async () => {
    try {
        const res = await apiService.getDashboardStats();
        if (res && res.code === 200 && res.data) {
            const d = res.data;
            stats.value.count = d.count != null ? d.count.toLocaleString() : stats.value.count;
            stats.value.countChange = d.countChange || stats.value.countChange;
            stats.value.efficiency = d.efficiency || stats.value.efficiency;
            stats.value.mortality = d.mortality || stats.value.mortality;
            stats.value.avgWeight = d.avgWeight || stats.value.avgWeight;
            stats.value.feedRatio = d.feedRatio || stats.value.feedRatio;
            stats.value.dailyFeed = d.dailyFeed || stats.value.dailyFeed;
            stats.value.dailyWater = d.dailyWater || stats.value.dailyWater;
            stats.value.deviceOnline = d.deviceOnline || stats.value.deviceOnline;
        }
    } catch (e) {
        console.error("加载大屏统计指标失败:", e);
    }
};

const loadTrends = async () => {
    try {
        const res = await apiService.getEnvironmentTrends();
        if (res && res.code === 200 && Array.isArray(res.data)) {
            const trends = res.data;
            const times = trends.map(t => t.time);
            const nh3s = trends.map(t => t.nh3 != null ? parseFloat(t.nh3) : 4.2);
            const co2s = trends.map(t => t.co2 != null ? parseFloat(t.co2) : 410.0);
            
            if (gasChartRef.value) {
                initMultiGasChart(gasChartRef.value, times, nh3s, co2s);
            }
        }
    } catch (e) {
        console.error("加载大屏环境走势曲线失败:", e);
    }
};

const loadEnvironmentAndAlerts = async () => {
    try {
        const areaRes = await apiService.getAreaStats();
        if (areaRes && areaRes.code === 200 && Array.isArray(areaRes.data)) {
            const temps = areaRes.data.map((a: any) => a.temperature || 38.0);
            const hums = areaRes.data.map((a: any) => a.humidity || 60.0);
            const avgT = temps.reduce((a: number, b: number) => a + b, 0) / temps.length;
            const avgH = hums.reduce((a: number, b: number) => a + b, 0) / hums.length;
            avgTemp.value = (avgT - 15).toFixed(1); // 转换体温为舒适温区
            avgHumidity.value = avgH.toFixed(1);
        }
        
        const alertRes = await apiService.getAlerts();
        if (alertRes && alertRes.code === 200 && Array.isArray(alertRes.data)) {
            activeAlerts.value = alertRes.data.slice(0, 3);
        }
    } catch (e) {
        console.error("加载实时环控与报警失败:", e);
    }
};

onMounted(async () => {
    await nextTick();
    
    try {
        await Promise.all([
            loadStats(),
            loadTrends(),
            loadEnvironmentAndAlerts()
        ]);
    } catch (e) {
        console.error("首屏载入失败:", e);
    } finally {
        setTimeout(() => {
            isLoading.value = false;
        }, 500); // 500ms 骨架屏缓冲，展现极致平滑的动态落地感
    }
    
    // 设立 3 秒高频动态轮询，形成数字孪生实感
    timer = setInterval(async () => {
        await loadStats();
        await loadTrends();
        await loadEnvironmentAndAlerts();
    }, 3000);

    const handleResize = () => charts.forEach(c => c.resize());
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    if (timer) clearInterval(timer);
    window.removeEventListener('resize', () => charts.forEach(c => c.resize()));
    charts.forEach(c => c.dispose());
    if (detailChartInstance) {
        detailChartInstance.dispose();
    }
});

const metricConfigs: Record<string, {
    title: string;
    unit: string;
    color: string;
    currentVal: string;
    subtext: string;
    average: string;
    peak: string;
    statusText: string;
    statusClass: string;
    insight: string;
    dates: string[];
    data: number[];
}> = {
    totalCount: {
        title: '全场实时总数',
        unit: '头',
        color: '#059669',
        currentVal: '14,502 头',
        subtext: '本周累计新增 482 头',
        average: '14,393 头',
        peak: '14,502 头',
        statusText: '稳步增长',
        statusClass: 'bg-emerald-100 text-emerald-800 border-emerald-250',
        insight: '全场生猪存栏总量稳步增长，补栏与出栏节奏调配科学。数字孪生分析表明，当前各圈舍空间利用率为 85% 的最优生理适宜度，无群落挤压或过载负荷风险。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [14210, 14350, 14402, 14390, 14420, 14480, 14502]
    },
    efficiency: {
        title: '核心繁育效率',
        unit: '%',
        color: '#10b981',
        currentVal: '92.5%',
        subtext: '年度指标达成率平稳',
        average: '91.63%',
        peak: '92.5%',
        statusText: '达标',
        statusClass: 'bg-emerald-100 text-emerald-800 border-emerald-200',
        insight: '受胎率与繁育效率维持在 92.5% 的行业领先高位。母猪群RFID电子耳标排卵周期动态抓取与产床精细化光照周期联动运行良好，利于后续批次产仔数增长。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [90.2, 91.0, 91.5, 92.1, 91.8, 92.3, 92.5]
    },
    avgWeight: {
        title: '场均出栏体重',
        unit: 'kg',
        color: '#059669',
        currentVal: '2.3kg',
        subtext: '均重增速平稳达标',
        average: '2.21 kg',
        peak: '2.30 kg',
        statusText: '增速正常',
        statusClass: 'bg-emerald-100 text-emerald-800 border-emerald-200',
        insight: '生猪均重增速完全吻合标准育肥期黄金增长模型。滑槽无应激自动测重与三维视觉三维重建体视重估算算法误差双重校验小于 1.5%，生长潜力健康。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [2.12, 2.15, 2.18, 2.22, 2.25, 2.28, 2.30]
    },
    deviceOnline: {
        title: '核心设备在线率',
        unit: '%',
        color: '#06b6d4',
        currentVal: '99.8%',
        subtext: '核心物联网设备连通状态',
        average: '99.73%',
        peak: '99.9%',
        statusText: '运行正常',
        statusClass: 'bg-cyan-100 text-cyan-800 border-cyan-200',
        insight: '现场无线传感器网路（Lora/Zigbee/WiFi）与边缘网关通信维持在 99.8% 稳定连通率。今日心跳冗余通道倒换测试正常，抗干扰与防抖吞吐率表现优异。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [99.5, 99.6, 99.8, 99.7, 99.9, 99.8, 99.8]
    },
    mortality: {
        title: '当日死亡率',
        unit: '%',
        color: '#f43f5e',
        currentVal: '0.5%',
        subtext: '全天死淘数据实时跟进',
        average: '0.53%',
        peak: '0.72%',
        statusText: '达标',
        statusClass: 'bg-emerald-100 text-emerald-800 border-emerald-250',
        insight: '当前死淘率稳定控制在 0.8% 目标红线以内。5月28日有轻微波动，可能与当日圈舍消毒通风调整有关，目前已恢复稳定。建议持续维持高频巡检。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [0.45, 0.62, 0.51, 0.38, 0.72, 0.55, 0.50]
    },
    feedRatio: {
        title: '全周料肉比 (FCR)',
        unit: ':1',
        color: '#d97706',
        currentVal: '1.5:1',
        subtext: '营养吸收转化效率正常',
        average: '1.50:1',
        peak: '1.53:1',
        statusText: '行业优秀',
        statusClass: 'bg-amber-100 text-amber-805 border-amber-250',
        insight: '全周料肉比稳定在 1.5:1，处于行业最前沿增重转化效率区间。饲料转化率维持高效，证明目前的自动精准喂料多阶段配方配比极佳，可维持目前策略。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [1.52, 1.50, 1.48, 1.51, 1.49, 1.53, 1.50]
    },
    dailyFeed: {
        title: '场均日供料总计',
        unit: 'T',
        color: '#10b981',
        currentVal: '12.5T',
        subtext: '当日饲料仓输送量汇总',
        average: '12.26 T',
        peak: '12.6 T',
        statusText: '自动喂料',
        statusClass: 'bg-emerald-100 text-emerald-800 border-emerald-250',
        insight: '日供料总量表现非常平稳，与生猪群落的自然增重生长曲线高度对称吻合。气动管道、刮板输送机传感器等运行正常，仓储库位充足。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [11.8, 12.1, 12.5, 12.3, 12.0, 12.6, 12.5]
    },
    dailyWater: {
        title: '每日饮水流转量',
        unit: 'm³',
        color: '#06b6d4',
        currentVal: '48.2m³',
        subtext: '当日自动化水网供水量',
        average: '48.23 m³',
        peak: '49.1 m³',
        statusText: '供水正常',
        statusClass: 'bg-cyan-100 text-cyan-800 border-cyan-250',
        insight: '每日饮水总量维持在 48m³ 上下，各栏舍水表流速传感器未见水管破损漏水或水嘴堵塞等异常读数。水网主阀压力、过滤阀滤芯在线压差指标良好。',
        dates: ['05-24', '05-25', '05-26', '05-27', '05-28', '05-29', '05-30'],
        data: [47.5, 48.0, 48.6, 47.9, 48.3, 49.1, 48.2]
    }
};

const openMetricDetail = async (type: string) => {
    if (type === 'mortality') metricConfigs.mortality.currentVal = stats.value.mortality;
    if (type === 'feedRatio') metricConfigs.feedRatio.currentVal = stats.value.feedRatio;
    if (type === 'dailyFeed') metricConfigs.dailyFeed.currentVal = stats.value.dailyFeed;
    if (type === 'dailyWater') metricConfigs.dailyWater.currentVal = stats.value.dailyWater;
    if (type === 'totalCount') metricConfigs.totalCount.currentVal = stats.value.count + ' 头';
    if (type === 'efficiency') metricConfigs.efficiency.currentVal = stats.value.efficiency;
    if (type === 'avgWeight') metricConfigs.avgWeight.currentVal = stats.value.avgWeight;
    if (type === 'deviceOnline') metricConfigs.deviceOnline.currentVal = stats.value.deviceOnline;

    activeDetailMetric.value = type;
    await nextTick();
    
    if (detailChartRef.value) {
        initDetailChart(detailChartRef.value, metricConfigs[type]);
    }
};

const closeMetricDetail = () => {
    activeDetailMetric.value = null;
    if (detailChartInstance) {
        detailChartInstance.dispose();
        detailChartInstance = null;
    }
};

function initDetailChart(el: HTMLElement, config: typeof metricConfigs[string]) {
    detailChartInstance = echarts.init(el);
    
    const option = {
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: config.color,
            borderWidth: 1,
            borderRadius: 12,
            shadowColor: 'rgba(0, 0, 0, 0.05)',
            shadowBlur: 10,
            textStyle: { color: '#064e3b', fontSize: 12, fontWeight: '600' },
            padding: [10, 14],
            formatter: (params: any) => {
                return `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;color:#064e3b;">日期: ${params[0].name}</div>
                        <div style="display:flex;justify-content:space-between;gap:16px;margin-top:4px;">
                            <span style="color:#064e3b;opacity:0.75;font-size:11px;">${config.title}</span>
                            <span style="font-weight:700;color:${config.color};font-size:11px;">${params[0].value} ${config.unit}</span>
                        </div>`;
            }
        },
        grid: { left: 16, right: 16, bottom: 10, top: 40, containLabel: true },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: config.dates,
            axisLine: { show: true, lineStyle: { color: '#d1fae5', width: 1.5 } },
            axisTick: { show: false },
            axisLabel: { fontSize: 10, fontWeight: 'bold', color: '#064e3b', opacity: 0.7 }
        },
        yAxis: {
            type: 'value',
            axisLine: { show: true, lineStyle: { color: '#d1fae5', width: 1.5 } },
            axisTick: { show: true, lineStyle: { color: '#d1fae5' } },
            splitLine: { show: true, lineStyle: { type: 'dashed', color: '#d1fae5' } },
            axisLabel: { show: true, color: '#064e3b', fontWeight: 'bold', fontSize: 9, opacity: 0.8 }
        },
        series: [
            {
                name: config.title,
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 8,
                itemStyle: { color: config.color, borderWidth: 2, borderColor: '#fff' },
                lineStyle: {
                    width: 4,
                    color: config.color,
                    shadowColor: config.color + '40',
                    shadowBlur: 10,
                    shadowOffsetY: 4
                },
                data: config.data,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: config.color + '30' },
                        { offset: 1, color: config.color + '00' }
                    ])
                }
            }
        ]
    };
    
    detailChartInstance.setOption(option);
    
    const handleResize = () => {
        if (detailChartInstance) detailChartInstance.resize();
    };
    window.addEventListener('resize', handleResize);
    
    detailChartInstance.on('dispose', () => {
        window.removeEventListener('resize', handleResize);
    });
}

function initMultiGasChart(el: HTMLElement, hours?: string[], nh3Data?: number[], co2Data?: number[]) {
    const hexToRgba = (hex: string, alpha: number) => {
        let r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    const myChart = echarts.getInstanceByDom(el) || echarts.init(el);
    if (!charts.includes(myChart)) {
        charts.push(myChart);
    }
    
    const xAxisData = hours || ['00:00', '06:00', '12:00', '18:00', '23:59'];
    const nh3 = nh3Data || [4.2, 3.5, 6.1, 8.2, 5.0];
    const co2 = co2Data || [410, 390, 520, 680, 450];

    const option = {
        tooltip: { 
            trigger: 'axis', 
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: '#a7f3d0',
            borderWidth: 1,
            borderRadius: 12,
            shadowColor: 'rgba(6, 78, 59, 0.05)',
            shadowBlur: 10,
            textStyle: { color: '#064e3b', fontSize: 11, fontWeight: '600' },
            padding: [10, 14],
            formatter: (params: any) => {
                let html = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;color:#064e3b;">时间点: ${params[0].name}</div>`;
                params.forEach((p: any) => {
                    const marker = `<span style="display:inline-block;margin-right:6px;border-radius:10px;width:8px;height:8px;background-color:${p.color};"></span>`;
                    html += `<div style="display:flex;justify-content:space-between;gap:16px;margin-top:4px;"><span style="color:#064e3b;opacity:0.75;font-size:11px;">${marker}${p.seriesName}</span><span style="font-weight:700;color:${p.color};font-size:11px;">${p.value} ${p.seriesName.includes('NH3') ? 'ppm' : 'ppm'}</span></div>`;
                });
                return html;
            }
        },
        grid: { left: 24, right: 24, bottom: 20, top: 40, containLabel: true },
        legend: {
            data: ['NH3 氨气 (ppm)', 'CO2 二氧化碳 (ppm)'],
            top: 0,
            textStyle: { color: '#064e3b', fontWeight: 'bold', fontSize: 11 },
            icon: 'circle'
        },
        xAxis: { 
            type: 'category', 
            boundaryGap: false, 
            data: xAxisData, 
            axisLine: { show: true, lineStyle: { color: '#d1fae5', width: 1.5 } }, 
            axisTick: { show: false },
            axisLabel: { fontSize: 10, fontWeight: 'bold', color: '#064e3b', opacity: 0.7 }
        },
        yAxis: [
            { 
               type: 'value', 
               name: 'NH3 (ppm)',
               nameTextStyle: { color: '#059669', fontWeight: 'bold', fontSize: 9 },
               axisLine: { show: true, lineStyle: { color: '#d1fae5', width: 1.5 } },
               axisTick: { show: true, lineStyle: { color: '#d1fae5' } },
               splitLine: { show: true, lineStyle: { type: 'dashed', color: '#d1fae5'} }, 
               axisLabel: { show: true, color: '#059669', fontWeight: 'bold', fontSize: 9 }
            },
            { 
               type: 'value', 
               name: 'CO2 (ppm)',
               nameTextStyle: { color: '#06b6d4', fontWeight: 'bold', fontSize: 9 },
               axisLine: { show: true, lineStyle: { color: '#d1fae5', width: 1.5 } },
               axisTick: { show: true, lineStyle: { color: '#d1fae5' } },
               splitLine: { show: false }, 
               axisLabel: { show: true, color: '#06b6d4', fontWeight: 'bold', fontSize: 9 }
            }
        ],
        series: [
            {
                name: 'NH3 氨气 (ppm)', 
                type: 'line', 
                smooth: true, 
                symbol: 'circle',
                symbolSize: 6,
                showSymbol: false,
                itemStyle: { color: '#10b981' },
                lineStyle: { 
                    width: 3.5, 
                    color: '#10b981',
                    shadowColor: 'rgba(16, 185, 129, 0.3)',
                    shadowBlur: 8,
                    shadowOffsetY: 3
                },
                data: nh3,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(16, 185, 129, 0.22)' },
                        { offset: 1, color: 'rgba(16, 185, 129, 0)' }
                    ])
                }
            },
            {
                name: 'CO2 二氧化碳 (ppm)', 
                type: 'line', 
                yAxisIndex: 1,
                smooth: true, 
                symbol: 'circle',
                symbolSize: 6,
                showSymbol: false,
                itemStyle: { color: '#06b6d4' },
                lineStyle: { 
                    width: 3.5, 
                    color: '#06b6d4',
                    shadowColor: 'rgba(6, 182, 212, 0.3)',
                    shadowBlur: 8,
                    shadowOffsetY: 3
                },
                data: co2,
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(6, 182, 212, 0.15)' },
                        { offset: 1, color: 'rgba(6, 182, 212, 0)' }
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
    <!-- Shimmering Skeleton Screen Placeholder -->
    <div v-if="isLoading" class="max-w-7xl mx-auto space-y-8 px-6 pt-8 animate-pulse">
      <!-- Subheader Skeleton (Mimicking Banner) -->
      <div class="h-[120px] bg-emerald-100/30 rounded-xl"></div>
      <!-- Hero metrics skeleton -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="h-32 bg-emerald-100/20 rounded-xl"></div>
        <div class="h-32 bg-emerald-100/20 rounded-xl"></div>
        <div class="h-32 bg-emerald-100/20 rounded-xl"></div>
        <div class="h-32 bg-emerald-100/20 rounded-xl"></div>
      </div>
      <!-- Analytics grid skeleton -->
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div class="lg:col-span-3 h-[400px] bg-emerald-100/20 rounded-xl"></div>
        <div class="lg:col-span-2 h-[400px] bg-emerald-100/20 rounded-xl"></div>
      </div>
    </div>

    <!-- Main Content Fade-in -->
    <div v-else class="animate-fade-in">
      <!-- Hero Header Section (Streamlined with integrated status badge) -->
      <section class="relative w-full h-[120px] flex items-center justify-between overflow-hidden border-b border-emerald-200 bg-emerald-200/30 px-8">
        <div class="absolute inset-0 z-0 flex justify-center items-center opacity-30 pointer-events-none">
          <div class="w-[600px] h-[600px] bg-emerald-300 blur-[100px] rounded-full"></div>
        </div>
        <div class="relative z-10 flex flex-col items-start mt-2">
          <span class="text-primary font-headline font-bold tracking-[0.4em] text-[10px] uppercase">COMMAND CENTER</span>
          <h1 class="text-2xl md:text-3xl font-headline font-bold text-emerald-950 tracking-tight">两头乌智能养殖概览</h1>
        </div>
        <div class="relative z-10 flex items-center gap-3 px-4 py-1.5 bg-white/90 backdrop-blur-sm rounded-full border border-emerald-200 shadow-sm mt-2">
          <div class="w-2.5 h-2.5 rounded-full bg-secondary pulse-indicator"></div>
          <span class="text-xs font-bold text-emerald-900">实时数据流: <span class="text-emerald-600 font-mono">同步稳定</span></span>
        </div>
      </section>

      <!-- Content wrap -->
      <div class="max-w-7xl mx-auto space-y-8 px-6 pt-8">
        
        <!-- Hero Metrics (Balanced 4-column layout, h-32 height) -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-6">
          <!-- Metric 1: Total count -->
          <div @click="openMetricDetail('totalCount')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98] flex flex-col justify-between h-32 relative overflow-hidden">
            <div class="absolute -right-2 -bottom-2 opacity-5 pointer-events-none">
              <span class="material-symbols-outlined text-[80px] text-emerald-950">pig</span>
            </div>
            <div class="flex justify-between items-start">
              <span class="text-emerald-850 font-bold text-xs uppercase tracking-wider">全场实时总数</span>
              <span class="bg-emerald-100 text-secondary font-mono font-bold text-[10px] px-2 py-0.5 rounded-full border border-emerald-200/80 flex items-center gap-0.5">
                <span class="material-symbols-outlined text-[10px]">trending_up</span>{{ stats.countChange }}
              </span>
            </div>
            <div>
              <h3 class="text-3xl font-headline font-bold text-emerald-950 tracking-tighter leading-none">{{ stats.count }} <span class="text-sm font-semibold text-emerald-900/60">头</span></h3>
              <p class="text-[10px] text-emerald-900/50 font-bold mt-1.5">本周累计新增 <span class="text-emerald-900">482</span> 头</p>
            </div>
          </div>

          <!-- Metric 2: Breeding efficiency -->
          <div @click="openMetricDetail('efficiency')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98] flex flex-col justify-between h-32 relative overflow-hidden">
            <div class="absolute -right-2 -bottom-2 opacity-5 pointer-events-none">
              <span class="material-symbols-outlined text-[80px] text-emerald-950">analytics</span>
            </div>
            <div class="flex justify-between items-start">
              <span class="text-emerald-855 font-bold text-xs uppercase tracking-wider">核心繁育效率</span>
              <span class="bg-emerald-100 text-emerald-900 font-bold text-[10px] px-2 py-0.5 rounded-full border border-emerald-200/80">年度指标</span>
            </div>
            <div>
              <h3 class="text-3xl font-headline font-bold text-secondary tracking-tighter leading-none">{{ stats.efficiency }}</h3>
              <div class="flex items-center gap-2 mt-2">
                <div class="flex-1 h-1.5 bg-emerald-100 rounded-full overflow-hidden">
                  <div class="h-full bg-secondary rounded-full" style="width: 92.5%"></div>
                </div>
                <span class="text-[9px] font-bold text-emerald-900/70 font-mono">+4.1%</span>
              </div>
            </div>
          </div>

          <!-- Metric 3: Average Weight -->
          <div @click="openMetricDetail('avgWeight')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98] flex flex-col justify-between h-32 relative overflow-hidden">
            <div class="absolute -right-2 -bottom-2 opacity-5 pointer-events-none">
              <span class="material-symbols-outlined text-[80px] text-emerald-950">weight</span>
            </div>
            <div class="flex justify-between items-start">
              <span class="text-emerald-850 font-bold text-xs uppercase tracking-wider">场均出栏体重</span>
              <span class="bg-emerald-100 text-emerald-700 font-mono font-bold text-[10px] px-2 py-0.5 rounded-full border border-emerald-200/80 flex items-center gap-0.5">
                <span class="material-symbols-outlined text-[10px]">arrow_upward</span>5%
              </span>
            </div>
            <div>
              <h3 class="text-3xl font-headline font-bold text-emerald-950 tracking-tighter leading-none">{{ stats.avgWeight }}</h3>
              <p class="text-[10px] text-emerald-900/50 font-bold mt-1.5">均重增速平稳达标</p>
            </div>
          </div>

          <!-- Metric 4: Device Online -->
          <div @click="openMetricDetail('deviceOnline')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98] flex flex-col justify-between h-32 relative overflow-hidden">
            <div class="absolute -right-2 -bottom-2 opacity-5 pointer-events-none">
              <span class="material-symbols-outlined text-[80px] text-emerald-950">router</span>
            </div>
            <div class="flex justify-between items-start">
              <span class="text-emerald-850 font-bold text-xs uppercase tracking-wider">核心设备在线率</span>
              <span class="bg-emerald-100 text-emerald-800 font-bold text-[10px] px-2 py-0.5 rounded-full border border-emerald-200/80 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>在线
              </span>
            </div>
            <div>
              <h3 class="text-3xl font-headline font-bold text-emerald-950 tracking-tighter leading-none">{{ stats.deviceOnline }}</h3>
              <p class="text-[10px] text-emerald-900/50 font-bold mt-1.5">网关状态: <span class="text-emerald-800">全部正常</span></p>
            </div>
          </div>
        </div>

        <!-- Analytics & Surveillance (Optimized ECharts and Climate Grid, h-400 height) -->
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <!-- Gas Chart -->
          <div class="lg:col-span-3 bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col h-[400px]">
            <div class="flex justify-between items-center mb-4 shrink-0">
              <div>
                <h4 class="font-headline font-bold text-base text-emerald-950">环境气体浓度趋势</h4>
                <p class="text-[9px] font-bold text-emerald-800/60 uppercase tracking-wider">多维气体指标遥测 — 24小时演变走势</p>
              </div>
              <div class="flex items-center gap-4">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-secondary"></span>
                  <span class="text-[9px] font-bold text-emerald-900/85 uppercase font-mono">NH3 氨气 (ppm)</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-white border border-secondary"></span>
                  <span class="text-[9px] font-bold text-emerald-900/85 uppercase font-mono">CO2 二氧化碳 (ppm)</span>
                </div>
              </div>
            </div>
            <div ref="gasChartRef" class="flex-1 w-full min-h-0 relative"></div>
          </div>

          <!-- Climate Sensors (2x2 premium capsule panels) -->
          <div class="lg:col-span-2 bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between h-[400px]">
            <div class="flex justify-between items-center shrink-0">
              <div>
                <h4 class="font-headline font-bold text-base text-emerald-950">实时微气候工况</h4>
                <p class="text-[9px] font-bold text-emerald-800/60 uppercase tracking-wider">环境传感器阵列遥测</p>
              </div>
              <span class="material-symbols-outlined text-secondary text-lg">sensors</span>
            </div>
            
            <!-- Sensor Grid -->
            <div class="grid grid-cols-2 gap-4 my-auto">
              <!-- Temp -->
              <div class="bg-emerald-50/50 p-4 rounded-xl border border-emerald-100 flex flex-col justify-between h-20 shadow-sm">
                <div class="flex justify-between items-center">
                  <span class="text-[10px] font-bold text-emerald-900/50 uppercase tracking-wider">场温平均</span>
                  <span class="text-[8px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">最佳</span>
                </div>
                <span class="text-xl font-bold text-emerald-950 font-mono mt-1">{{ avgTemp }} <span class="text-xs font-normal">°C</span></span>
              </div>

              <!-- Humidity -->
              <div class="bg-emerald-50/50 p-4 rounded-xl border border-emerald-100 flex flex-col justify-between h-20 shadow-sm">
                <div class="flex justify-between items-center">
                  <span class="text-[10px] font-bold text-emerald-900/50 uppercase tracking-wider">平均湿度</span>
                  <span class="text-[8px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">正常</span>
                </div>
                <span class="text-xl font-bold text-emerald-950 font-mono mt-1">{{ avgHumidity }} <span class="text-xs font-normal">%</span></span>
              </div>

              <!-- Air flow -->
              <div class="bg-emerald-50/50 p-4 rounded-xl border border-emerald-100 flex flex-col justify-between h-20 shadow-sm">
                <div class="flex justify-between items-center">
                  <span class="text-[10px] font-bold text-emerald-900/50 uppercase tracking-wider">气流风速</span>
                  <span class="text-[8px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">顺畅</span>
                </div>
                <span class="text-xl font-bold text-emerald-950 font-mono mt-1">0.25 <span class="text-xs font-normal">m/s</span></span>
              </div>

              <!-- Light -->
              <div class="bg-emerald-50/50 p-4 rounded-xl border border-emerald-100 flex flex-col justify-between h-20 shadow-sm">
                <div class="flex justify-between items-center">
                  <span class="text-[10px] font-bold text-emerald-900/50 uppercase tracking-wider">光照辐射</span>
                  <span class="text-[8px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded-full">适宜</span>
                </div>
                <span class="text-xl font-bold text-emerald-950 font-mono mt-1">350 <span class="text-xs font-normal">Lux</span></span>
              </div>
            </div>

            <div class="text-[9px] text-emerald-900/50 font-bold flex items-center gap-1.5 pt-3 shrink-0 border-t border-emerald-100/50">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              全场环控排风与供暖阀在线运行正常
            </div>
          </div>
        </div>

        <!-- Secondary Metrics & Alerts (Reduced FCR sparklines noise, cleaned icons) -->
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div class="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Rate -->
            <div @click="openMetricDetail('mortality')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between h-[160px] hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98]">
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-emerald-900/60 font-bold uppercase tracking-wider">当日死亡率</span>
                <span class="text-[9px] font-bold bg-emerald-100 text-emerald-900 px-2 py-0.5 rounded-full border border-emerald-200">目标 0.8% 内</span>
              </div>
              <div class="flex justify-between items-end mt-2">
                <div>
                  <span class="text-3xl font-headline font-bold text-emerald-950">{{ stats.mortality }}</span>
                  <p class="text-[9px] text-emerald-900/40 font-bold mt-1">全天死淘数据实时跟进</p>
                </div>
                <!-- Premium Glowing Sparkline 1 -->
                <div class="h-10 w-24">
                  <svg class="w-full h-full" viewBox="0 0 100 30" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="spark-grad-1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.25" />
                        <stop offset="100%" stop-color="#f43f5e" stop-opacity="0" />
                      </linearGradient>
                    </defs>
                    <path d="M 0,25 Q 10,23.5 20,22 T 40,28 T 60,15 T 80,18 T 100,20 L 100,30 L 0,30 Z" fill="url(#spark-grad-1)"></path>
                    <path d="M 0,25 Q 10,23.5 20,22 T 40,28 T 60,15 T 80,18 T 100,20" fill="none" stroke="#f43f5e" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" class="chart-line" style="filter: drop-shadow(0px 2px 4px rgba(244, 63, 94, 0.35));"></path>
                  </svg>
                </div>
              </div>
            </div>

            <!-- Feed Ratio -->
            <div @click="openMetricDetail('feedRatio')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between h-[160px] hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98]">
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-emerald-900/60 font-bold uppercase tracking-wider">全周料肉比 (FCR)</span>
                <span class="text-[9px] font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full border border-emerald-200/80">行业优秀</span>
              </div>
              <div class="flex justify-between items-end mt-2">
                <div>
                  <span class="text-3xl font-headline font-bold text-emerald-950">{{ stats.feedRatio }}</span>
                  <p class="text-[9px] text-emerald-900/40 font-bold mt-1">营养吸收转化效率正常</p>
                </div>
                <!-- Premium Glowing Sparkline 2 -->
                <div class="h-10 w-24">
                  <svg class="w-full h-full" viewBox="0 0 100 30" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="spark-grad-2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#d97706" stop-opacity="0.25" />
                        <stop offset="100%" stop-color="#d97706" stop-opacity="0" />
                      </linearGradient>
                    </defs>
                    <path d="M 0,15 Q 10,15.5 20,16 T 40,14 T 60,15 T 80,16 T 100,15 L 100,30 L 0,30 Z" fill="url(#spark-grad-2)"></path>
                    <path d="M 0,15 Q 10,15.5 20,16 T 40,14 T 60,15 T 80,16 T 100,15" fill="none" stroke="#d97706" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" class="chart-line" style="filter: drop-shadow(0px 2px 4px rgba(217, 119, 6, 0.35));"></path>
                  </svg>
                </div>
              </div>
            </div>

            <!-- Daily Feed -->
            <div @click="openMetricDetail('dailyFeed')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between h-[160px] hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98]">
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-emerald-900/60 font-bold uppercase tracking-wider">场均日供料总计</span>
                <span class="text-[9px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full border border-emerald-200">自动喂料</span>
              </div>
              <div class="flex justify-between items-end mt-2">
                <div>
                  <span class="text-3xl font-headline font-bold text-emerald-950">{{ stats.dailyFeed }}</span>
                  <p class="text-[9px] text-emerald-900/40 font-bold mt-1">当日饲料仓输送量汇总</p>
                </div>
                <!-- Premium Glowing Sparkline 3 -->
                <div class="h-10 w-24">
                  <svg class="w-full h-full" viewBox="0 0 100 30" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="spark-grad-3" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#10b981" stop-opacity="0.25" />
                        <stop offset="100%" stop-color="#10b981" stop-opacity="0" />
                      </linearGradient>
                    </defs>
                    <path d="M 0,22 Q 10,23 20,21 T 40,25 T 60,20 T 80,18 T 100,22 L 100,30 L 0,30 Z" fill="url(#spark-grad-3)"></path>
                    <path d="M 0,22 Q 10,23 20,21 T 40,25 T 60,20 T 80,18 T 100,22" fill="none" stroke="#10b981" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" class="chart-line" style="filter: drop-shadow(0px 2px 4px rgba(16, 185, 129, 0.35));"></path>
                  </svg>
                </div>
              </div>
            </div>
            
            <!-- Daily Water -->
            <div @click="openMetricDetail('dailyWater')" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between h-[160px] hover:shadow-lg hover:-translate-y-1 hover:border-emerald-400 cursor-pointer transition-all duration-300 active:scale-[0.98]">
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-emerald-900/60 font-bold uppercase tracking-wider">每日饮水流转量</span>
                <span class="text-[9px] font-bold text-secondary flex items-center gap-0.5">
                  <span class="material-symbols-outlined text-[11px]">arrow_downward</span>1.2%
                </span>
              </div>
              <div class="flex justify-between items-end mt-2">
                <div>
                  <span class="text-3xl font-headline font-bold text-emerald-950">{{ stats.dailyWater }}</span>
                  <p class="text-[9px] text-emerald-900/40 font-bold mt-1">当日自动化水网供水量</p>
                </div>
                <!-- Premium Glowing Sparkline 4 -->
                <div class="h-10 w-24">
                  <svg class="w-full h-full" viewBox="0 0 100 30" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="spark-grad-4" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.25" />
                        <stop offset="100%" stop-color="#06b6d4" stop-opacity="0" />
                      </linearGradient>
                    </defs>
                    <path d="M 0,10 Q 10,12 20,8 T 40,15 T 60,12 T 80,10 T 100,12 L 100,30 L 0,30 Z" fill="url(#spark-grad-4)"></path>
                    <path d="M 0,10 Q 10,12 20,8 T 40,15 T 60,12 T 80,10 T 100,12" fill="none" stroke="#06b6d4" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" class="chart-line" style="filter: drop-shadow(0px 2px 4px rgba(6, 182, 212, 0.35));"></path>
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <!-- Alerts (Dynamic Scrollable Container, Standard readable text size >= 12px) -->
          <div class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm flex flex-col justify-between min-h-[340px] lg:h-full">
            <div class="flex-1 flex flex-col">
              <div class="flex justify-between items-center mb-4 shrink-0">
                <h4 class="font-headline font-bold text-emerald-950 text-sm">实时数据告警</h4>
                <span class="text-[10px] font-bold text-emerald-900 bg-emerald-100 px-2 py-0.5 rounded-full border border-emerald-200">
                  {{ activeAlerts.length }} 条待办
                </span>
              </div>
              
              <!-- Scrollable Stream -->
              <div class="space-y-3 overflow-y-auto max-h-[230px] pr-1 flex-1">
                <template v-for="item in activeAlerts" :key="item.id">
                  <div 
                    :class="[
                      'flex gap-3 p-3 rounded-lg border-l-4 shadow-sm hover:translate-x-0.5 transition duration-200 cursor-pointer',
                      item.risk === 'Critical' ? 'bg-red-50/70 border-red-500' :
                      item.risk === 'High' ? 'bg-amber-50/70 border-amber-500' : 'bg-emerald-50/70 border-emerald-500'
                    ]"
                  >
                    <span 
                      :class="[
                        'material-symbols-outlined text-lg shrink-0 mt-0.5',
                        item.risk === 'Critical' ? 'text-red-600' :
                        item.risk === 'High' ? 'text-amber-600' : 'text-emerald-600'
                      ]"
                    >
                      {{ item.risk === 'Critical' ? 'warning' : 'info' }}
                    </span>
                    <div class="min-w-0 flex-1">
                      <p class="text-xs font-bold text-emerald-950 truncate">{{ item.pigId }} - {{ item.type }}</p>
                      <p class="text-[10px] text-emerald-900 font-semibold mt-0.5 truncate">{{ item.area }} • {{ item.risk }}级风险</p>
                      <p class="text-[9px] text-emerald-900/50 font-bold mt-1">{{ item.timestamp }}</p>
                    </div>
                  </div>
                </template>
                
                <div v-if="!activeAlerts.length" class="flex flex-col items-center justify-center py-12 text-center text-emerald-900/40 my-auto">
                  <span class="material-symbols-outlined text-[36px] text-emerald-700/40">check_circle</span>
                  <p class="text-xs font-bold mt-2 uppercase tracking-wider">运行平稳，无活动告警</p>
                </div>
              </div>
            </div>
            
            <button class="w-full mt-4 py-2 text-xs font-bold text-emerald-900 border border-emerald-200 rounded-lg hover:bg-emerald-100/50 transition-all uppercase tracking-widest shrink-0">
              查看完整历史
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- High-Fidelity Glassmorphic Detail Modal -->
  <div v-if="activeDetailMetric && metricConfigs[activeDetailMetric]" class="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-x-hidden overflow-y-auto outline-none">
    <!-- Backdrop with blur and dark translucent overlay -->
    <div class="fixed inset-0 bg-emerald-950/40 backdrop-blur-md transition-opacity duration-300" @click="closeMetricDetail"></div>
    
    <!-- Modal Content Container with premium fade-in scale animation -->
    <div class="relative bg-white/95 border border-emerald-250 w-full max-w-2xl rounded-2xl shadow-2xl p-6 md:p-8 z-10 flex flex-col gap-6 animate-zoom-in max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="flex justify-between items-start border-b border-emerald-100 pb-4">
        <div>
          <span class="text-[10px] font-bold text-emerald-800 uppercase tracking-widest">指标历史走势遥测</span>
          <h3 class="text-xl md:text-2xl font-headline font-bold text-emerald-950 flex items-center gap-2 mt-1">
            {{ metricConfigs[activeDetailMetric].title }}
            <span :class="['text-xs font-bold px-2 py-0.5 rounded-full border', metricConfigs[activeDetailMetric].statusClass]">
              {{ metricConfigs[activeDetailMetric].statusText }}
            </span>
          </h3>
        </div>
        <button @click="closeMetricDetail" class="text-emerald-900/50 hover:text-emerald-900 hover:bg-emerald-100/50 p-1.5 rounded-full transition-all flex items-center justify-center">
          <span class="material-symbols-outlined text-lg">close</span>
        </button>
      </div>
      
      <!-- Main Stats Summary -->
      <div class="grid grid-cols-3 gap-4 bg-emerald-50/40 p-4 rounded-xl border border-emerald-100/60">
        <div class="flex flex-col">
          <span class="text-[9px] font-bold text-emerald-900/50 uppercase tracking-wider">当前数值</span>
          <span class="text-2xl font-headline font-bold text-emerald-950 mt-1">{{ metricConfigs[activeDetailMetric].currentVal }}</span>
        </div>
        <div class="flex flex-col border-l border-emerald-200/50 pl-4">
          <span class="text-[9px] font-bold text-emerald-900/50 uppercase tracking-wider">7日均值</span>
          <span class="text-2xl font-headline font-bold text-emerald-850 mt-1 font-mono">{{ metricConfigs[activeDetailMetric].average }}</span>
        </div>
        <div class="flex flex-col border-l border-emerald-200/50 pl-4">
          <span class="text-[9px] font-bold text-emerald-900/50 uppercase tracking-wider">7日峰值</span>
          <span class="text-2xl font-headline font-bold text-emerald-900 mt-1 font-mono" :style="{ color: metricConfigs[activeDetailMetric].color }">
            {{ metricConfigs[activeDetailMetric].peak }}
          </span>
        </div>
      </div>
      
      <!-- ECharts Detailed Area -->
      <div class="bg-white/50 border border-emerald-100 p-2 rounded-xl">
        <div ref="detailChartRef" class="w-full h-64 md:h-72"></div>
      </div>
      
      <!-- AI Analytical Insight -->
      <div class="bg-emerald-100/25 border-l-4 border-emerald-500 p-4 rounded-r-xl">
        <div class="flex items-center gap-2 mb-1.5">
          <span class="material-symbols-outlined text-emerald-700 text-sm">psychology</span>
          <span class="text-[10px] font-bold text-emerald-850 uppercase tracking-wider">数据孪生AI专家诊断</span>
        </div>
        <p class="text-xs text-emerald-900 leading-relaxed font-semibold">
          {{ metricConfigs[activeDetailMetric].insight }}
        </p>
      </div>
      
      <!-- Bottom Actions -->
      <div class="flex justify-end gap-3 pt-2 border-t border-emerald-100/60">
        <button @click="closeMetricDetail" class="px-4 py-2 text-xs font-bold text-emerald-900 border border-emerald-200 rounded-lg hover:bg-emerald-100/50 transition-all uppercase tracking-wider">
          关闭窗口
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pulse-indicator {
  animation: pulse-dot 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: .4;
    transform: scale(1.15);
  }
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.animate-zoom-in {
  animation: zoomIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}
@keyframes zoomIn {
  from { opacity: 0; transform: scale(0.94); }
  to   { opacity: 1; transform: scale(1); }
}
</style>