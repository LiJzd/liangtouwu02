<script setup lang="ts">
// 实时监控：纯视频流展示版（已移除 AI 解析）
import { ref, onMounted } from 'vue';
import { cn } from '../utils';

// 摄像头数据结构
interface CameraData {
  id: number;
  name: string;
  status: 'online' | 'offline';
  location: string;
  videoFile: string;
  type: 'mp4' | 'stream';
}

const cameras = ref<CameraData[]>([
  { 
    id: 1, 
    name: '保育区 - 核心监控 #01', 
    status: 'online', 
    location: '保育舍核心层',
    videoFile: 'monitor_v3.mp4',
    type: 'mp4'
  },
  { 
    id: 101, 
    name: '2 号猪舍 - 实时监控 (LIVE)', 
    status: 'online', 
    location: '2 号舍西北角',
    videoFile: 'live',
    type: 'stream'
  },
  { 
    id: 2, 
    name: '测试源 - 历史画面', 
    status: 'online', 
    location: '模拟场景',
    videoFile: '4abdf5306f1a7165dc7eca7ed3f39f3e.mp4',
    type: 'mp4'
  }
]);

const selectedCamera = ref<CameraData | null>(null);
const currentTime = ref(new Date().toLocaleTimeString());
const videoUrl = ref('');
const videoKey = ref(0); 

const selectCamera = (cam: CameraData) => {
  selectedCamera.value = cam;
  if (cam.status === 'online' && cam.videoFile) {
    if (cam.type === 'stream') {
      const baseUrl = import.meta.env.VITE_AI_SERVICE_URL || 'http://localhost:8000';
      videoUrl.value = `${baseUrl}/api/v1/perception/stream/${cam.videoFile}`;
    } else {
      videoUrl.value = `/${cam.videoFile}`;
    }
    videoKey.value++; 
  } else {
    videoUrl.value = '';
  }
};

onMounted(() => {
  const firstOnline = cameras.value.find(c => c.status === 'online');
  if (firstOnline) {
    selectCamera(firstOnline);
  }
  
  setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString();
  }, 1000);
});
</script>

<template>
  <div class="flex flex-col lg:flex-row h-[calc(100vh-8rem)] gap-6">
    
    <!-- 信号源列表 -->
    <div class="w-full lg:w-80 bg-white/90 backdrop-blur-md rounded-2xl border border-emerald-200 flex flex-col overflow-hidden shadow-sm">
      <div class="p-5 border-b border-emerald-100 bg-surface-container-low">
        <h2 class="font-headline font-bold text-emerald-950 flex items-center uppercase tracking-widest text-sm">
          <span class="material-symbols-outlined mr-2 text-secondary text-lg">videocam</span>
          实况监控列表
        </h2>
      </div>
      <div class="flex-1 overflow-y-auto p-0 space-y-0 divide-y divide-emerald-50">
        <button
          v-for="cam in cameras"
          :key="cam.id"
          @click="selectCamera(cam)"
          :class="cn(
            'w-full text-left p-5 transition-all hover:bg-emerald-50 relative overflow-hidden group',
            selectedCamera?.id === cam.id
              ? 'bg-emerald-50/80 before:absolute before:inset-y-0 before:left-0 before:w-1 before:bg-secondary'
              : ''
          )"
        >
          <div class="flex justify-between items-start">
            <span :class="cn('font-bold font-headline text-sm uppercase', selectedCamera?.id === cam.id ? 'text-secondary' : 'text-emerald-900')">
                {{ cam.name }}
            </span>
            <span :class="cn('text-[10px] px-2 py-0.5 font-bold uppercase tracking-widest rounded-full border', cam.status === 'online' ? 'bg-emerald-100 border-emerald-200 text-emerald-800' : 'bg-red-100 border-red-200 text-red-700')">
              {{ cam.status === 'online' ? '在线' : '离线' }}
            </span>
          </div>
          <p class="text-[10px] text-emerald-900/50 mt-2 font-inter uppercase tracking-wide flex items-center">
            <span class="material-symbols-outlined text-[12px] mr-1">location_on</span>
            {{ cam.location }}
          </p>
        </button>
      </div>
    </div>

    <!-- 视频播放器 -->
    <div class="flex-1 bg-inverse-surface rounded-2xl border border-emerald-900/50 overflow-hidden relative group shadow-2xl flex flex-col justify-center">
      <template v-if="selectedCamera">
        
        <!-- 时间叠加层 -->
        <div class="absolute top-6 right-6 text-emerald-400 text-xs font-headline bg-black/40 px-3 py-1.5 rounded-full z-20 border border-emerald-900/20 backdrop-blur-md">
          {{ currentTime }}
        </div>

        <div class="w-full h-full flex items-center justify-center bg-[#0a0f12] relative overflow-hidden">
           <!-- 网格背景 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:60px_60px] pointer-events-none z-0"></div>
          
           <!-- CRT 扫描线特效 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.2)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,255,0,0.03))] bg-[size:100%_4px,3px_100%] pointer-events-none z-30"></div>

          <!-- 视频层 -->
          <div v-if="videoUrl" class="relative w-full h-full flex items-center justify-center z-10">
              <img 
                v-if="selectedCamera.type === 'stream'"
                :key="videoKey"
                :src="videoUrl"
                class="max-w-full max-h-full object-contain"
                alt="实时监控流"
              />
              <video
                v-else
                :key="videoKey"
                class="max-w-full max-h-full object-contain"
                autoplay
                loop
                muted
              >
                <source :src="videoUrl" type="video/mp4" />
                您的浏览器不支持视频播放
              </video>
          </div>
          
          <!-- 信号丢失提示 -->
          <div v-else class="text-center z-10">
              <span class="material-symbols-outlined text-[64px] mx-auto mb-4 opacity-20 text-white block">videocam_off</span>
              <span class="text-xl font-headline font-bold text-white/60 uppercase tracking-widest block">信号丢失 / NO SIGNAL</span>
              <p class="text-xs text-white/30 mt-3 font-mono">设备源: {{ selectedCamera.name }}</p>
          </div>
        </div>

        <!-- 控制条 -->
        <div class="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center justify-center space-x-3 translate-y-24 group-hover:translate-y-0 transition-transform duration-300 z-40 bg-black/60 backdrop-blur-xl border border-white/10 px-6 py-3 rounded-full">
          <button class="p-2 hover:bg-white/10 text-white rounded-full transition-colors flex items-center justify-center" title="快照">
            <span class="material-symbols-outlined text-xl">photo_camera</span>
          </button>
          <div class="w-px h-6 bg-white/20 mx-2"></div>
          <button class="p-2 hover:bg-white/10 text-white rounded-full transition-colors flex items-center justify-center" title="全屏">
            <span class="material-symbols-outlined text-xl">fullscreen</span>
          </button>
        </div>
      </template>
      <div v-else class="w-full h-full flex items-center justify-center text-white/30 font-headline font-bold text-lg uppercase tracking-widest">
        就绪 - 请选择实况节点
      </div>
    </div>
  </div>
</template>
