<script setup lang="ts">
// 实时监控：集成 YOLO 检测流
import { ref, onMounted } from 'vue';
import { Camera, Video, Maximize, Scissors, CircleDot, RefreshCw } from 'lucide-vue-next';
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
    <div class="w-full lg:w-80 bg-white rounded-none border border-slate-300 flex flex-col overflow-hidden">
      <div class="p-4 border-b border-slate-300 bg-slate-50">
        <h2 class="font-bold text-slate-800 flex items-center uppercase tracking-widest text-sm">
          <Camera class="w-4 h-4 mr-2 text-blue-600" />
          多路监控信号
        </h2>
      </div>
      <div class="flex-1 overflow-y-auto p-0 space-y-0 divide-y divide-slate-100">
        <button
          v-for="cam in cameras"
          :key="cam.id"
          @click="selectCamera(cam)"
          :class="cn(
            'w-full text-left p-4 transition-all hover:bg-slate-50 border-l-4',
            selectedCamera?.id === cam.id
              ? 'border-blue-600 bg-blue-50'
              : 'border-transparent'
          )"
        >
          <div class="flex justify-between items-start">
            <span :class="cn('font-bold font-mono text-sm uppercase', selectedCamera?.id === cam.id ? 'text-blue-700' : 'text-slate-700')">
                {{ cam.name }}
            </span>
            <span :class="cn('text-[10px] px-1 py-0.5 font-bold uppercase tracking-wider', cam.status === 'online' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700')">
              {{ cam.status === 'online' ? '在线' : '离线' }}
            </span>
          </div>
          <p class="text-[10px] text-slate-400 mt-1 font-mono uppercase tracking-wide">区域: {{ cam.location }}</p>
        </button>
      </div>
    </div>

    <!-- 视频播放器 -->
    <div class="flex-1 bg-black rounded-none border border-slate-800 overflow-hidden relative group shadow-none flex flex-col justify-center">
      <template v-if="selectedCamera">
        <!-- 录制状态 -->
        <div class="absolute top-4 left-4 bg-red-600 text-white text-[10px] font-bold px-2 py-1 rounded-none animate-pulse flex items-center z-20 uppercase tracking-widest border border-red-500">
          <CircleDot class="w-3 h-3 mr-2" /> LIVE 实时侦测
        </div>
        
        <!-- 算法信息 -->
        <div class="absolute top-4 right-4 text-blue-500 text-xs font-mono bg-black/60 px-2 py-1 rounded-none z-20 border border-blue-900/50">
          感知引擎: YOLOv10-M | {{ currentTime }}
        </div>
        
        <!-- AI服务状态 -->
        <div class="absolute top-16 right-4 bg-blue-600/20 text-blue-400 text-[10px] font-bold px-2 py-1 border border-blue-500/30 z-20 uppercase tracking-widest backdrop-blur-sm">
          AI服务: {{ streamError ? '连接失败' : '正常' }}
        </div>

        <!-- 刷新按钮 -->
        <button 
          @click="refreshStream"
          class="absolute top-28 right-4 bg-slate-800/80 hover:bg-slate-700 text-white text-[10px] font-bold px-2 py-1 border border-slate-600 z-20 uppercase tracking-widest backdrop-blur-sm flex items-center gap-1 transition-colors"
        >
          <RefreshCw class="w-3 h-3" /> 刷新
        </button>

        <div class="w-full h-full flex items-center justify-center bg-slate-950 relative overflow-hidden">
           <!-- 网格背景 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-0"></div>
          
           <!-- CRT 扫描线特效 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,255,0,0.03))] bg-[size:100%_4px,3px_100%] pointer-events-none z-30"></div>

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
              <Video class="w-16 h-16 mx-auto mb-4 opacity-20 text-red-500" />
              <span class="text-xl font-mono text-red-600 uppercase tracking-widest block">AI服务连接失败</span>
              <p class="text-[10px] text-slate-700 mt-2 font-mono">请确保AI服务已启动: python ai-service/main.py</p>
              <button 
                @click="refreshStream"
                class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold uppercase tracking-widest border border-blue-500 transition-colors"
              >
                重试连接
              </button>
          </div>
          
          <!-- 离线提示 -->
          <div v-else class="text-center z-10">
              <Video class="w-16 h-16 mx-auto mb-4 opacity-20 text-slate-500" />
              <span class="text-xl font-mono text-slate-600 uppercase tracking-widest block">信号丢失 / NO SIGNAL</span>
              <p class="text-[10px] text-slate-700 mt-2 font-mono">设备源: {{ selectedCamera.name }}</p>
          </div>
        </div>

        <!-- 控制条 -->
        <div class="absolute bottom-0 left-0 right-0 bg-slate-900/90 border-t border-slate-800 p-4 translate-y-full group-hover:translate-y-0 transition-transform duration-200 z-20">
          <div class="flex items-center justify-center space-x-4">
            <button 
              @click="refreshStream"
              class="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold uppercase tracking-widest border border-slate-600 transition-colors flex items-center"
            >
              <RefreshCw class="w-4 h-4 mr-2" />
              刷新流
            </button>
            <button class="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold uppercase tracking-widest border border-slate-600 transition-colors flex items-center">
              <CircleDot class="w-4 h-4 mr-2 text-red-500" /> 取证录制
            </button>
            <button class="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold uppercase tracking-widest border border-slate-600 transition-colors flex items-center">
              <Scissors class="w-4 h-4 mr-2" /> 瞬时快照
            </button>
            <button class="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold uppercase tracking-widest border border-slate-600 transition-colors flex items-center">
              <Maximize class="w-4 h-4 mr-2" /> 剧院模式
            </button>
          </div>
        </div>
      </template>
      <div v-else class="w-full h-full flex items-center justify-center text-slate-600 font-mono uppercase tracking-widest">
        就绪 - 请选择监控节点
      </div>
    </div>
  </div>
</template>
