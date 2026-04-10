<script setup lang="ts">
import { ref } from 'vue';

// 喂食系统状态
const feedingStatus = ref({
    active: false,
    nextTime: '12:00',
    progress: 0,
    amount: 2.5, // kg
    history: [
        { time: '06:00', amount: '2.5kg', status: '完成' },
        { time: '09:00', amount: '1.2kg', status: '完成' },
    ]
});

// 给水系统状态
const wateringStatus = ref({
    active: true,
    pressure: 0.35, // MPa
    dailyUsage: 42.8, // m³
    flowRate: 1.2, // L/min
});

// 设备控制列表
const devices = ref([
    { id: 'fan-1', name: '01栋主风扇', type: 'fan', state: true, value: 65, icon: 'mode_fan' },
    { id: 'light-1', name: '保育舍照明', type: 'light', state: false, value: 0, icon: 'lightbulb' },
    { id: 'temp-1', name: '恒温空调系统', type: 'temp', state: true, value: 24, icon: 'thermostat' },
    { id: 'camera-ptz', name: '云台摄像机', type: 'camera', state: true, value: null, icon: 'videocam' },
]);

function toggleFeeding() {
    feedingStatus.value.active = !feedingStatus.value.active;
    if (feedingStatus.value.active) {
        // 模拟进度
        let p = 0;
        const interval = setInterval(() => {
            p += 5;
            feedingStatus.value.progress = p;
            if (p >= 100) {
                clearInterval(interval);
                setTimeout(() => {
                    feedingStatus.value.active = false;
                    feedingStatus.value.progress = 0;
                }, 1000);
            }
        }, 100);
    }
}

function toggleDevice(id: string) {
    const device = devices.value.find(d => d.id === id);
    if (device) device.state = !device.state;
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
        <span class="text-primary font-headline font-bold tracking-[0.4em] text-[10px] mb-2 uppercase">REMOTE CONTROL</span>
        <h1 class="text-3xl md:text-4xl font-headline font-bold text-emerald-950 tracking-tight">远程控制与自动化中心</h1>
      </div>
    </section>

    <!-- Content wrap -->
    <div class="max-w-7xl mx-auto space-y-8 px-6 pt-8">
      
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- 自动喂食控制 -->
        <div class="lg:col-span-2 space-y-6">
          <div class="bg-white/95 p-8 rounded-xl border border-emerald-200 shadow-sm flex flex-col h-full hover:shadow-md transition-all">
            <div class="flex justify-between items-start mb-8">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span class="material-symbols-outlined text-primary text-xl">restaurant</span>
                  <h3 class="text-xl font-headline font-bold text-emerald-950">自动喂食系统</h3>
                </div>
                <p class="text-[10px] font-bold text-emerald-800/80 uppercase tracking-wider">智能精准投喂控制单元</p>
              </div>
              <div :class="`px-3 py-1 rounded-full text-[10px] font-bold border ${feedingStatus.active ? 'bg-emerald-100 text-secondary border-emerald-200' : 'bg-slate-100 text-slate-500 border-slate-200'}`">
                {{ feedingStatus.active ? '投喂中' : '待机中' }}
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
              <div class="space-y-6">
                <div>
                  <label class="text-[10px] font-bold text-emerald-900 uppercase tracking-widest block mb-4">投喂计划详情</label>
                  <div class="space-y-3">
                    <div class="flex justify-between items-center py-2 border-b border-emerald-100">
                      <span class="text-xs text-on-surface-variant font-medium">下次自动投喂</span>
                      <span class="text-xs font-bold text-emerald-950 font-headline">{{ feedingStatus.nextTime }}</span>
                    </div>
                    <div class="flex justify-between items-center py-2 border-b border-emerald-100">
                      <span class="text-xs text-on-surface-variant font-medium">标准投喂量</span>
                      <span class="text-xs font-bold text-emerald-950 font-headline">{{ feedingStatus.amount }} kg/头</span>
                    </div>
                  </div>
                </div>

                <div v-if="feedingStatus.active">
                  <div class="flex justify-between items-end mb-2">
                    <span class="text-[10px] font-bold text-secondary uppercase">当前进度</span>
                    <span class="text-xs font-bold text-secondary">{{ feedingStatus.progress }}%</span>
                  </div>
                  <div class="w-full h-2 bg-emerald-100 rounded-full overflow-hidden">
                    <div class="h-full bg-secondary transition-all duration-300" :style="`width: ${feedingStatus.progress}%`"></div>
                  </div>
                </div>

                <button 
                  @click="toggleFeeding"
                  :disabled="feedingStatus.active"
                  class="w-full py-4 bg-emerald-950 text-white rounded-xl font-headline font-bold text-sm hover:bg-emerald-900 active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span class="material-symbols-outlined text-lg">{{ feedingStatus.active ? 'sync' : 'bolt' }}</span>
                  {{ feedingStatus.active ? '正在执行投喂操作...' : '立即启动手动投喂' }}
                </button>
              </div>

              <div class="bg-emerald-50/50 rounded-xl p-6 border border-emerald-100">
                <h4 class="text-[10px] font-bold text-emerald-900 uppercase tracking-widest mb-4">今日投喂历史</h4>
                <div class="space-y-4">
                  <div v-for="(log, i) in feedingStatus.history" :key="i" class="flex items-center gap-4">
                    <div class="w-2 h-2 rounded-full bg-secondary"></div>
                    <div class="flex-1">
                      <div class="flex justify-between">
                        <span class="text-xs font-bold text-emerald-950 font-headline">{{ log.time }}</span>
                        <span class="text-[10px] font-bold text-secondary">{{ log.status }}</span>
                      </div>
                      <p class="text-[10px] text-on-surface-variant font-medium">完成配额：{{ log.amount }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 自动喂水控制 -->
        <div class="space-y-6">
          <div class="bg-white/95 p-8 rounded-xl border border-emerald-200 shadow-sm flex flex-col h-full hover:shadow-md transition-all">
            <div class="flex justify-between items-start mb-8">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span class="material-symbols-outlined text-primary text-xl">water_drop</span>
                  <h3 class="text-xl font-headline font-bold text-emerald-950">自动供水中心</h3>
                </div>
                <p class="text-[10px] font-bold text-emerald-800/80 uppercase tracking-wider">场内饮用水资源调度</p>
              </div>
              <div class="w-3 h-3 rounded-full bg-secondary pulse-indicator"></div>
            </div>

            <div class="flex-1 space-y-8">
              <div class="grid grid-cols-2 gap-4">
                <div class="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                  <p class="text-[9px] font-bold text-emerald-900 uppercase mb-1">当前水压</p>
                  <p class="text-xl font-headline font-bold text-emerald-950">{{ wateringStatus.pressure }} <span class="text-[10px] font-normal">MPa</span></p>
                </div>
                <div class="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                  <p class="text-[9px] font-bold text-emerald-900 uppercase mb-1">实时流速</p>
                  <p class="text-xl font-headline font-bold text-emerald-950">{{ wateringStatus.flowRate }} <span class="text-[10px] font-normal">L/min</span></p>
                </div>
              </div>

              <div>
                <div class="flex justify-between items-center mb-4">
                  <label class="text-[10px] font-bold text-emerald-900 uppercase tracking-widest">供水控制开关</label>
                  <div @click="wateringStatus.active = !wateringStatus.active" :class="`w-10 h-5 rounded-full relative cursor-pointer transition-colors duration-300 ${wateringStatus.active ? 'bg-secondary' : 'bg-slate-300'}`">
                    <div :class="`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 ${wateringStatus.active ? 'translate-x-5' : ''}`"></div>
                  </div>
                </div>
                <p class="text-xs text-on-surface-variant leading-relaxed">主供水管道当前处于 <span :class="wateringStatus.active ? 'text-secondary font-bold' : 'text-slate-500 font-bold'">{{ wateringStatus.active ? '开启' : '关闭' }}</span> 状态。自动稳压系统已就绪。</p>
              </div>

              <div class="pt-6 border-t border-emerald-100">
                <div class="flex justify-between items-end mb-2">
                    <span class="text-[10px] font-bold text-emerald-900 uppercase">今日累积消耗情况</span>
                    <span class="text-xs font-bold text-emerald-950 font-headline">{{ wateringStatus.dailyUsage }} m³</span>
                </div>
                <div class="h-10 w-full mt-1">
                   <svg class="w-full h-full opacity-60 chart-line" viewBox="0 0 100 30" preserveAspectRatio="none">
                     <path d="M 0,25 Q 15,20 30,22 T 50,15 T 75,18 T 100,20" fill="none" stroke="#059669" stroke-linecap="round" stroke-width="2.5"></path>
                   </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 远程设备列表 -->
      <section>
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
          <div>
            <span class="text-primary font-headline font-bold tracking-widest text-[10px] uppercase">EQUIPMENT CLOUD</span>
            <h2 class="text-xl font-headline font-bold text-emerald-950 mt-1">云端设备集群控制</h2>
          </div>
          <div class="flex items-center gap-2">
            <button class="px-4 py-1.5 bg-emerald-100 text-secondary text-[10px] font-bold rounded-full border border-emerald-200">一键重置所有设备</button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div v-for="device in devices" :key="device.id" class="bg-white/95 p-6 rounded-xl border border-emerald-200 shadow-sm hover:-translate-y-1 transition duration-300 group">
            <div class="flex justify-between items-start mb-6">
              <div :class="`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${device.state ? 'bg-emerald-100 text-secondary' : 'bg-slate-100 text-slate-400'}`">
                <span class="material-symbols-outlined text-2xl" :class="device.state && device.type === 'fan' ? 'animate-spin-slow' : ''">{{ device.icon }}</span>
              </div>
              <div @click="toggleDevice(device.id)" :class="`w-10 h-5 rounded-full relative cursor-pointer transition-colors duration-300 ${device.state ? 'bg-secondary' : 'bg-slate-300'}`">
                <div :class="`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform duration-300 ${device.state ? 'translate-x-5' : ''}`"></div>
              </div>
            </div>

            <div>
              <h4 class="text-sm font-bold text-emerald-950 mb-1">{{ device.name }}</h4>
              <p class="text-[10px] text-on-surface-variant/70 font-bold uppercase tracking-widest">{{ device.state ? '运行中' : '离线/已关闭' }}</p>
            </div>

            <div v-if="device.value !== null" class="mt-6">
              <div class="flex justify-between text-[10px] font-bold text-emerald-800 mb-2">
                <span>{{ device.type === 'temp' ? '设定温度' : '功率输出' }}</span>
                <span>{{ device.value }}{{ device.type === 'temp' ? '°C' : '%' }}</span>
              </div>
              <div class="w-full h-1 bg-emerald-50 rounded-full overflow-hidden">
                <div class="h-full bg-secondary transition-all" :style="`width: ${device.type === 'temp' ? (device.value / 40) * 100 : device.value}%`"></div>
              </div>
            </div>
            
            <div v-else class="mt-6 h-[26px] flex items-center text-[10px] font-bold text-secondary">
               <span class="material-symbols-outlined text-xs mr-1">check_circle</span> 链路连接正常
            </div>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>

<style scoped>
.pulse-indicator {
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin-slow {
  animation: spin-slow 3s linear infinite;
}
</style>
