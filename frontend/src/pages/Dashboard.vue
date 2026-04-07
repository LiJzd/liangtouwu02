<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';

const stats = ref({
    count: '14,502',
    countChange: '+125',
    efficiency: '92.5',
    efficiencyChange: '+1.2',
    mortality: '0.5',
    avgWeight: '2.3',
    feedRatio: '1.5:1',
    dailyFeed: '12.5',
    dailyWater: '48.2'
});

const matrixHeatmapRef = ref<HTMLElement | null>(null);
const nh3ChartRef = ref<HTMLElement | null>(null);
const co2ChartRef = ref<HTMLElement | null>(null);
const h2sChartRef = ref<HTMLElement | null>(null);

let charts: echarts.ECharts[] = [];

// 滚动交互状态
const stickyContainerRef = ref<HTMLElement | null>(null);
const trackX = ref(0);
const activePanelIndex = ref(0);

const onScroll = () => {
    if (!stickyContainerRef.value) return;
    const containerRect = stickyContainerRef.value.getBoundingClientRect();
    const stickyTopOffset = 80; // top-20
    const scrollDistance = stickyTopOffset - containerRect.top;
    
    if (scrollDistance >= 0) {
        const stickyHeight = window.innerHeight * 0.8;
        const maxScroll = containerRect.height - stickyHeight - stickyTopOffset;
        let progress = scrollDistance / (maxScroll > 0 ? maxScroll : 1);
        progress = Math.max(0, Math.min(1, progress));
        
        // 轨道横移控制
        trackX.value = -(progress * 66.66666);
        
        // 导航高亮
        if (progress < 0.33) activePanelIndex.value = 0;
        else if (progress < 0.66) activePanelIndex.value = 1;
        else activePanelIndex.value = 2;
    } else {
        trackX.value = 0;
        activePanelIndex.value = 0;
    }
};

onMounted(async () => {
    await nextTick();
    if (matrixHeatmapRef.value) initMatrixHeatmap(matrixHeatmapRef.value);
    
    if (nh3ChartRef.value) initGasTrendChart(nh3ChartRef.value, '氨气(NH3)', '#3b82f6', [3.2, 3.8, 5.5, 4.2, 6.1, 4.8, 3.5], 5.0, 'ppm');
    if (co2ChartRef.value) initGasTrendChart(co2ChartRef.value, '二氧化碳(CO2)', '#10b981', [380, 410, 480, 450, 520, 460, 390], 450, 'ppm');
    if (h2sChartRef.value) initGasTrendChart(h2sChartRef.value, '硫化氢(H2S)', '#f59e0b', [0.05, 0.08, 0.12, 0.09, 0.15, 0.11, 0.06], 0.1, 'ppm');

    const handleResize = () => charts.forEach(c => c.resize());
    window.addEventListener('resize', handleResize);
    window.addEventListener('scroll', onScroll, { passive: true });
});

onUnmounted(() => {
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('resize', () => charts.forEach(c => c.resize()));
    charts.forEach(c => c.dispose());
});
function initGasTrendChart(el: HTMLElement, name: string, color: string, data: number[], _currentValue: number, unit: string) {
    const hexToRgba = (hex: string, alpha: number) => {
        let r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    const myChart = echarts.init(el);
    charts.push(myChart);
    const hours = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'];
    const option = {
        title: { text: name + ' 趋势', textStyle: { color: color, fontSize: 28, fontWeight: 'bold' }, left: 'center', top: 20 },
        tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)' },
        grid: { left: 60, right: 60, bottom: 60, top: 100 },
        xAxis: { type: 'category', boundaryGap: false, data: hours, axisLine:{lineStyle:{color:'#cbd5e1'}}, axisLabel:{fontSize: 16, fontWeight:'bold', color: '#64748b'} },
        yAxis: { type: 'value', name: unit, splitLine: { lineStyle: { type: 'dashed', color:'#e2e8f0'} }, axisLabel:{fontSize: 16, fontWeight:'bold', color: '#64748b'}, nameTextStyle:{fontSize: 16, color: '#64748b'} },
        series: [
            {
                name: name, type: 'line', smooth: true, symbolSize: 14,
                lineStyle: { width: 6, color: color },
                itemStyle: { color: color, shadowBlur: 10, shadowColor: color }, 
                data: data,
                markPoint: {
                    data: [{ type: 'max', name: 'Max' }],
                    itemStyle: {color: color}
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: hexToRgba(color, 0.4) },
                        { offset: 1, color: hexToRgba(color, 0) }
                    ])
                }
            }
        ]
    };
    
    myChart.setOption(option);
}

function initMatrixHeatmap(el: HTMLElement) {
    const myChart = echarts.init(el);
    charts.push(myChart);
    const xData = ['A级', 'B级', 'C级', 'D级', 'E级', 'F级'];
    const yData = ['6区', '5区', '4区', '3区', '2区', '1区'];
    const data = [];
    for(let i=0; i<6; i++) {
        for(let j=0; j<6; j++) {
            const dist = Math.abs(i - 2.5) + Math.abs(j - 2.5);
            data.push([i, j, Math.max(0, 10 - dist * 2 + Math.floor(Math.random() * 3))]);
        }
    }
    
    myChart.setOption({
        grid: { top: 20, right: 30, bottom: 30, left: 60 },
        xAxis: { type: 'category', data: xData, splitArea: { show: true }, axisLine: {show: false}, axisTick: {show: false}, axisLabel:{fontSize: 16, fontWeight:'bold', color: '#475569'} },
        yAxis: { type: 'category', data: yData, splitArea: { show: true }, axisLine: {show: false}, axisTick: {show: false}, axisLabel:{fontSize: 16, fontWeight:'bold', color: '#475569'} },
        visualMap: {
            min: 0, max: 12, calculable: true, orient: 'vertical',
            right: 0, top: 'center', itemHeight: 250, itemWidth: 30,
            inRange: { color: ['#eff6ff', '#bae6fd', '#38bdf8', '#0284c7', '#0f172a'] }
        },
        series: [{
            name: 'Risk Level',
            type: 'heatmap',
            data: data,
            label: { show: true, fontSize: 18, fontWeight: 'bold', color: '#fff' },
            itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 4 }
        }]
    });
}
</script>

<template>
  <div class="flex flex-col pb-40 pt-10 w-[95%] mx-auto max-w-[2000px] relative scroll-smooth">
    
    <!-- 统计指标 -->
    <section v-reveal="{delay: 100, arg: 'fade'}" class="flex flex-col space-y-16 mt-12 mb-48 px-2 shrink-0">
        <div class="flex items-baseline space-x-44">
            <div>
                <h3 class="text-2xl font-extrabold text-slate-500 tracking-wider mb-2 uppercase">全场实时总计数 (头)</h3>
                <div class="flex items-end">
                    <div class="text-[8rem] leading-[0.8] font-black text-[#0f172a] tracking-tighter">{{ stats.count }}</div>
                    <div class="ml-6 mb-4 px-4 py-2 bg-emerald-100 text-emerald-700 rounded-2xl text-2xl font-black shadow-sm">{{ stats.countChange }}</div>
                </div>
            </div>
            <div>
                <h3 class="text-2xl font-extrabold text-slate-500 tracking-wider mb-2 uppercase">核心繁育效率 (%)</h3>
                <div class="flex items-end">
                    <div class="text-[8rem] leading-[0.8] font-black text-[#0f172a] tracking-tighter">{{ stats.efficiency }}</div>
                    <span class="text-[6rem] leading-[0.8] font-black text-[#0f172a] tracking-tighter ml-2">%</span>
                    <div class="ml-6 mb-4 px-4 py-2 bg-blue-100 text-blue-700 rounded-2xl text-2xl font-black shadow-sm">{{ stats.efficiencyChange }}</div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-5 gap-8">
            <div v-reveal="{delay: 200, arg: 'blur-in'}" class="bg-white/95 backdrop-blur-md border-[1.5px] border-white/50 p-8 rounded-[2rem] shadow-[0_10px_40px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_50px_rgba(0,0,0,0.08)] transition-all duration-500 hover:-translate-y-2 group">
                <p class="text-xl font-bold text-slate-500 mb-6 tracking-wider">当日死亡率</p>
                <div class="flex items-baseline">
                    <span class="text-6xl font-black text-[#0f172a] tracking-tight group-hover:text-red-500 transition-colors">{{ stats.mortality }}</span>
                    <span class="ml-2 text-3xl font-bold text-slate-400 group-hover:text-red-400 transition-colors">%</span>
                </div>
            </div>
            
            <div v-reveal="{delay: 350, arg: 'blur-in'}" class="bg-white/95 backdrop-blur-md border-[1.5px] border-white/50 p-8 rounded-[2rem] shadow-[0_10px_40px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_50px_rgba(0,0,0,0.08)] transition-all duration-500 hover:-translate-y-2 group">
                <p class="text-xl font-bold text-slate-500 mb-6 tracking-wider">场均体重</p>
                <div class="flex items-baseline">
                    <span class="text-6xl font-black text-[#0f172a] tracking-tight group-hover:text-emerald-500 transition-colors">{{ stats.avgWeight }}</span>
                    <span class="ml-2 text-3xl font-bold text-slate-400 group-hover:text-emerald-400 transition-colors">kg</span>
                </div>
            </div>

            <div v-reveal="{delay: 500, arg: 'blur-in'}" class="bg-white/95 backdrop-blur-md border-[1.5px] border-white/50 p-8 rounded-[2rem] shadow-[0_10px_40px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_50px_rgba(0,0,0,0.08)] transition-all duration-500 hover:-translate-y-2 group">
                <p class="text-xl font-bold text-slate-500 mb-6 tracking-wider">全周期料肉比</p>
                <div class="flex items-baseline">
                    <span class="text-6xl font-black text-[#0f172a] tracking-tight group-hover:text-amber-500 transition-colors">{{ stats.feedRatio }}</span>
                </div>
            </div>

            <div v-reveal="{delay: 650, arg: 'blur-in'}" class="bg-white/95 backdrop-blur-md border-[1.5px] border-white/50 p-8 rounded-[2rem] shadow-[0_10px_40px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_50px_rgba(0,0,0,0.08)] transition-all duration-500 hover:-translate-y-2 group">
                <p class="text-xl font-bold text-slate-500 mb-6 tracking-wider">日供料量</p>
                <div class="flex items-baseline">
                    <span class="text-6xl font-black text-[#0f172a] tracking-tight group-hover:text-indigo-500 transition-colors">{{ stats.dailyFeed }}</span>
                    <span class="ml-2 text-3xl font-bold text-slate-400 group-hover:text-indigo-400 transition-colors">T</span>
                </div>
            </div>

            <div v-reveal="{delay: 800, arg: 'blur-in'}" class="bg-white/95 backdrop-blur-md border-[1.5px] border-white/50 p-8 rounded-[2rem] shadow-[0_10px_40px_rgba(0,0,0,0.04)] hover:shadow-[0_15px_50px_rgba(0,0,0,0.08)] transition-all duration-500 hover:-translate-y-2 group">
                <p class="text-xl font-bold text-slate-500 mb-6 tracking-wider">日供水量</p>
                <div class="flex items-baseline">
                    <span class="text-6xl font-black text-[#0f172a] tracking-tight group-hover:text-cyan-500 transition-colors">{{ stats.dailyWater }}</span>
                    <span class="ml-2 text-3xl font-bold text-slate-400 group-hover:text-cyan-400 transition-colors">m³</span>
                </div>
            </div>
        </div>
    </section>

    <!-- 气体传感系统 -->
    <div ref="stickyContainerRef" class="relative w-full shrink-0 mb-32" style="height: 350vh;">
        <div class="sticky top-20 w-full h-[80vh] bg-white rounded-[3.5rem] shadow-[0_30px_90px_rgba(0,0,0,0.08)] overflow-hidden flex flex-col border border-slate-100">
            <!-- Header -->
            <div class="px-16 pt-12 pb-6 flex items-center justify-between shrink-0 relative z-20 bg-gradient-to-b from-white to-white/90 backdrop-blur-sm">
                <div>
                    <h2 class="text-4xl font-black text-[#0f172a] tracking-widest relative z-10 before:content-[''] before:absolute before:bottom-1 before:-left-4 before:w-[120%] before:h-6 before:bg-blue-100/60 before:-z-10">微环境传感纵览系统</h2>
                    <p class="text-slate-400 font-bold tracking-widest mt-4 uppercase text-lg">环境指标动态监测</p>
                </div>
                <!-- 分页指示器 -->
                <div class="flex space-x-6 bg-slate-50 p-4 rounded-full border border-slate-100">
                    <div :class="['w-16 h-2 rounded-full transition-all duration-500', activePanelIndex === 0 ? 'bg-blue-500 scale-110 shadow-[0_0_10px_rgba(59,130,246,0.5)]' : 'bg-slate-200']"></div>
                    <div :class="['w-16 h-2 rounded-full transition-all duration-500', activePanelIndex === 1 ? 'bg-emerald-500 scale-110 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-slate-200']"></div>
                    <div :class="['w-16 h-2 rounded-full transition-all duration-500', activePanelIndex === 2 ? 'bg-amber-500 scale-110 shadow-[0_0_10px_rgba(245,158,11,0.5)]' : 'bg-slate-200']"></div>
                </div>
            </div>

            <!-- 传感器展示轨道 -->
            <div 
                class="flex-1 w-[300%] flex flex-nowrap transition-transform ease-out will-change-transform duration-100"
                :style="{ transform: `translate3d(${trackX}%, 0, 0)` }"
            >
                <!-- Section 1: NH3 -->
                <div class="w-1/3 h-full flex px-16 pb-12 items-center justify-center">
                    <div class="w-[35%] h-full flex flex-col justify-center pr-16 border-r-2 border-slate-100/60">
                         <div class="mb-4 text-blue-500 font-black text-2xl tracking-[0.5em]">PHASE 01</div>
                         <h1 class="text-8xl font-black text-[#0f172a] mb-6 tracking-tighter">氨气 <br/><span class="text-blue-500">NH3</span></h1>
                         <p class="text-slate-500 text-xl leading-relaxed font-semibold">源于极度灵敏的传感薄膜矩阵，实时分析并解构高致密度氨气的流变趋势，辅助通风系统的动态闭环调节。</p>
                         <div class="mt-auto bg-blue-50 p-6 rounded-3xl border border-blue-100">
                             <div class="text-slate-400 font-bold mb-2">当前瞬时浓度</div>
                             <div class="text-5xl font-black text-blue-600">5.0 <span class="text-2xl text-blue-400">ppm</span></div>
                         </div>
                    </div>
                    <div ref="nh3ChartRef" class="flex-1 h-full pt-8 pl-10"></div>
                </div>

                <!-- Section 2: CO2 -->
                <div class="w-1/3 h-full flex px-16 pb-12 items-center justify-center">
                    <div class="w-[35%] h-full flex flex-col justify-center pr-16 border-r-2 border-slate-100/60">
                         <div class="mb-4 text-emerald-500 font-black text-2xl tracking-[0.5em]">PHASE 02</div>
                         <h1 class="text-8xl font-black text-[#0f172a] mb-6 tracking-tighter">二氧化碳 <br/><span class="text-emerald-500">CO2</span></h1>
                         <p class="text-slate-500 text-xl leading-relaxed font-semibold">采用非色散红外吸收(NDIR)技术原理，针对畜牧微环境实现千分级精准碳浓度测绘，防范围控盲区缺氧风险。</p>
                         <div class="mt-auto bg-emerald-50 p-6 rounded-3xl border border-emerald-100">
                             <div class="text-slate-400 font-bold mb-2">当前瞬时浓度</div>
                             <div class="text-5xl font-black text-emerald-600">450 <span class="text-2xl text-emerald-400">ppm</span></div>
                         </div>
                    </div>
                    <div ref="co2ChartRef" class="flex-1 h-full pt-8 pl-10"></div>
                </div>

                <!-- Section 3: H2S -->
                <div class="w-1/3 h-full flex px-16 pb-12 items-center justify-center">
                    <div class="w-[35%] h-full flex flex-col justify-center pr-16 border-r-2 border-slate-100/60">
                         <div class="mb-4 text-amber-500 font-black text-2xl tracking-[0.5em]">PHASE 03</div>
                         <h1 class="text-8xl font-black text-[#0f172a] mb-6 tracking-tighter">硫化氢 <br/><span class="text-amber-500">H2S</span></h1>
                         <p class="text-slate-500 text-xl leading-relaxed font-semibold">特种耐腐蚀光电离电极实时嗅探，通过亚 ppm 级预警机制精准抓取有害气体突发泄露，构建生物安全屏障。</p>
                         <div class="mt-auto bg-amber-50 p-6 rounded-3xl border border-amber-100">
                             <div class="text-slate-400 font-bold mb-2">当前瞬时浓度</div>
                             <div class="text-5xl font-black text-amber-600">0.10 <span class="text-2xl text-amber-400">ppm</span></div>
                         </div>
                    </div>
                    <div ref="h2sChartRef" class="flex-1 h-full pt-8 pl-10"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 风险矩阵 -->
    <section v-reveal="{delay: 150, arg: 'blur-in'}" class="bg-white border border-slate-100 rounded-[2.5rem] p-12 shadow-[0_10px_40px_rgba(0,0,0,0.03)] relative overflow-hidden transition-all duration-500 hover:shadow-[0_20px_60px_rgba(0,0,0,0.06)] flex flex-col space-y-10 w-full shrink-0">
        <div class="flex items-center justify-between">
            <h2 class="text-3xl font-black text-[#0f172a] tracking-widest px-4 relative z-10 before:content-[''] before:absolute before:bottom-1 before:left-0 before:w-full before:h-5 before:bg-blue-100/80 before:-z-10">全局风险控制 - 热力源分布</h2>
            <div class="text-slate-400 cursor-pointer hover:text-slate-800 transition-colors font-bold text-4xl">···</div>
        </div>
        <div ref="matrixHeatmapRef" class="w-full h-[600px] relative z-20"></div>
        <div class="absolute bottom-[-150px] left-1/4 w-1/2 h-[300px] bg-gradient-to-t from-blue-100 via-cyan-100 to-transparent blur-[80px] opacity-30 rounded-[100%] pointer-events-none z-0"></div>
    </section>

  </div>
</template>
