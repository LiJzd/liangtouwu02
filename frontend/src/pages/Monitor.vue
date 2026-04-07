<script setup lang="ts">
// 实时监控：集成 YOLO 检测流
import { ref, onMounted } from 'vue';
import { cn } from '../utils';

// 摄像头数据结构
interface CameraData {
  id: number;
  name: string;
  status: 'online' | 'offline';
  location: string;
  videoFile: string;
}

// 状态管理
const AI_SERVICE_URL = 'http://localhost:8000';

const cameras = ref<CameraData[]>([
  { 
    id: 1, 
    name: '保育区 - 西南角 #15', 
    status: 'online', 
    location: '保育舍西南',
    videoFile: '保育-西南角_20250409000000-20250411000000_15.mp4'
  },
  { 
    id: 2, 
    name: '保育区 - 西南角 #23', 
    status: 'online', 
    location: '保育舍西南',
    videoFile: '保育-西南角_20250409000000-20250411000000_23.mp4'
  },
  { 
    id: 3, 
    name: '保育区 - 东南角 #19', 
    status: 'online', 
    location: '保育舍东南',
    videoFile: '保育-东南角_20250409000000-20250411000000_19.mp4'
  },
  { 
    id: 4, 
    name: '监控廊道', 
    status: 'offline', 
    location: '办公区',
    videoFile: ''
  }
]);

const selectedCamera = ref<CameraData | null>(null);
const currentTime = ref(new Date().toLocaleTimeString());
const streamUrl = ref('');
const streamError = ref(false);
const streamKey = ref(0); // 强制刷新标签

const selectCamera = (cam: CameraData) => {
  selectedCamera.value = cam;
  streamError.value = false;
  
  if (cam.status === 'online' && cam.videoFile) {
    // 构建AI服务的MJPEG流URL
    streamUrl.value = `${AI_SERVICE_URL}/api/v1/perception/stream/${encodeURIComponent(cam.videoFile)}`;
    streamKey.value++; // 强制刷新
  } else {
    streamUrl.value = '';
  }
};

const refreshStream = () => {
  if (selectedCamera.value) {
    streamKey.value++;
    streamError.value = false;
  }
};

const handleStreamError = () => {
  streamError.value = true;
  console.error('视频流加载失败:', streamUrl.value);
};

onMounted(() => {
  // 默认选中第一个在线摄像头
  const firstOnline = cameras.value.find(c => c.status === 'online');
  if (firstOnline) {
    selectCamera(firstOnline);
  }
  
  // 更新时钟
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
          多路监控信号
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
        <!-- 录制状态 -->
        <div class="absolute top-6 left-6 bg-red-600/90 text-white text-[10px] font-bold px-3 py-1.5 rounded-full animate-pulse flex items-center z-20 uppercase tracking-widest backdrop-blur-sm border border-red-500/50">
          <span class="w-2 h-2 rounded-full bg-white mr-2"></span> LIVE 实时侦测
        </div>
        
        <!-- 算法信息 -->
        <div class="absolute top-6 right-6 text-secondary text-xs font-headline bg-black/60 px-3 py-1.5 rounded-full z-20 border border-secondary/30 backdrop-blur-md shadow-lg">
          感知引擎: YOLOv10-M | {{ currentTime }}
        </div>
        
        <!-- AI服务状态 -->
        <div class="absolute top-16 right-6 bg-inverse-primary/20 text-secondary text-[10px] font-bold px-3 py-1.5 rounded-full border border-secondary/20 z-20 uppercase tracking-widest backdrop-blur-md">
          AI服务: {{ streamError ? '连接失败' : '正常' }}
        </div>

        <!-- 刷新按钮 -->
        <button 
          @click="refreshStream"
          class="absolute top-28 right-6 bg-black/50 hover:bg-black/80 text-white text-[10px] font-bold px-3 py-1.5 rounded-full border border-white/10 z-20 uppercase tracking-widest backdrop-blur-md flex items-center gap-1.5 transition-colors"
        >
          <span class="material-symbols-outlined text-[14px]">refresh</span> 刷新
        </button>

        <div class="w-full h-full flex items-center justify-center bg-[#0a0f12] relative overflow-hidden">
           <!-- 网格背景 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:60px_60px] pointer-events-none z-0"></div>
          
           <!-- CRT 扫描线特效 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.2)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,255,0,0.03))] bg-[size:100%_4px,3px_100%] pointer-events-none z-30"></div>

          <!-- MJPEG 视频流 -->
          <div v-if="streamUrl && !streamError" class="relative w-full h-full flex items-center justify-center z-10">
              <img 
                :key="streamKey"
                :src="streamUrl" 
                class="max-w-full max-h-full object-contain"
                alt="实时AI检测视频流"
                @error="handleStreamError"
              />
          </div>
          
          <!-- 错误提示 -->
          <div v-else-if="streamError" class="text-center z-10">
              <span class="material-symbols-outlined text-[64px] mx-auto mb-4 opacity-30 text-red-500 block">videocam_off</span>
              <span class="text-xl font-headline font-bold text-red-500 uppercase tracking-widest block">AI服务连接失败</span>
              <p class="text-xs text-white/40 mt-3 font-mono">请确保AI服务已启动: python ai-service/main.py</p>
              <button 
                @click="refreshStream"
                class="mt-6 px-6 py-2.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 text-xs font-bold uppercase tracking-widest rounded-full border border-red-500/30 transition-colors"
              >
                重试连接
              </button>
          </div>
          
          <!-- 离线提示 -->
          <div v-else class="text-center z-10">
              <span class="material-symbols-outlined text-[64px] mx-auto mb-4 opacity-20 text-white block">videocam_off</span>
              <span class="text-xl font-headline font-bold text-white/60 uppercase tracking-widest block">信号丢失 / NO SIGNAL</span>
              <p class="text-xs text-white/30 mt-3 font-mono">设备源: {{ selectedCamera.name }}</p>
          </div>
        </div>

        <!-- 控制条 -->
        <div class="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center justify-center space-x-3 translate-y-24 group-hover:translate-y-0 transition-transform duration-300 z-40 bg-black/60 backdrop-blur-xl border border-white/10 px-6 py-3 rounded-full">
          <button 
            @click="refreshStream"
            class="p-2 hover:bg-white/10 text-white rounded-full transition-colors flex items-center justify-center" title="刷新流"
          >
            <span class="material-symbols-outlined text-xl">refresh</span>
          </button>
          <div class="w-px h-6 bg-white/20 mx-2"></div>
          <button class="p-2 hover:bg-white/10 text-white rounded-full transition-colors flex items-center justify-center" title="取证录制">
            <span class="material-symbols-outlined text-xl text-red-500">radio_button_checked</span>
          </button>
          <button class="p-2 hover:bg-white/10 text-white rounded-full transition-colors flex items-center justify-center" title="瞬时快照">
            <span class="material-symbols-outlined text-xl">content_cut</span>
          </button>
          <button class="p-2 hover:bg-white/10 text-white rounded-full transition-colors flex items-center justify-center" title="剧院模式">
            <span class="material-symbols-outlined text-xl">fullscreen</span>
          </button>
        </div>
      </template>
      <div v-else class="w-full h-full flex items-center justify-center text-white/30 font-headline font-bold text-lg uppercase tracking-widest">
        就绪 - 请选择左侧监控节点
      </div>
    </div>
  </div>
</template>
