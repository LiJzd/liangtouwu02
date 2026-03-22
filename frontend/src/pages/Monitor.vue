<script setup lang="ts">
/**
 * 实时监控 (Monitor) 视图组件
 * =====================================
 * 本组件是系统的视觉感知核心，负责集成物理摄像头流与本地视频模拟流。
 * 
 * 核心功能：
 * 1. 动态信号源切换：支持在多个摄像头/录像文件间一键切换。
 * 2. AI 标注集成：视频流并非原始画面，而是经过 Python AI 端渲染了 YOLO 检出框后的“增强现实”流。
 * 3. 沉浸式 UI：采用网格背景、扫描线特效及脉冲动画，营造工业级监控站的视觉氛围。
 */
import { ref, onMounted } from 'vue';
import { Camera, Video, Maximize, Scissors, CircleDot } from 'lucide-vue-next';
import { apiService } from '../api';
import { Camera as CameraType } from '../api';
import { cn } from '../utils';

// --- 状态管理 ---
const cameras = ref<CameraType[]>([]);
const selectedCamera = ref<CameraType | null>(null);
const loading = ref(true);
const currentTime = ref(new Date().toLocaleTimeString()); // 用于 HUD 时钟显示

onMounted(async () => {
    try {
        // 从后端（Java 端透传）获取摄像头列表
        const res = await apiService.getCameras();
        cameras.value = res; // 直接使用返回的数组
        // 默认选中第一个可用信号
        if (cameras.value.length > 0) {
            selectedCamera.value = cameras.value[0];
        }
    } finally {
        loading.value = false;
    }
    
    // HUD 时钟每秒更新
    setInterval(() => {
        currentTime.value = new Date().toLocaleTimeString();
    }, 1000);
});

/** 切换当前查看的信号源 */
const selectCamera = (cam: CameraType) => {
    selectedCamera.value = cam;
}
</script>

<template>
  <div v-if="loading" class="p-10 text-center text-slate-500 font-mono uppercase">系统自检中...</div>
  <div v-else class="flex flex-col lg:flex-row h-[calc(100vh-8rem)] gap-6">
    
    <!-- 左侧：信号源列表 -->
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

    <!-- 右侧：视频播放器与 HUD 覆盖层 -->
    <div class="flex-1 bg-black rounded-none border border-slate-800 overflow-hidden relative group shadow-none flex flex-col justify-center">
      <template v-if="selectedCamera">
        <!-- HUD: 录制状态 -->
        <div class="absolute top-4 left-4 bg-red-600 text-white text-[10px] font-bold px-2 py-1 rounded-none animate-pulse flex items-center z-10 uppercase tracking-widest border border-red-500">
          <CircleDot class="w-3 h-3 mr-2" /> LIVE 实时侦测
        </div>
        
        <!-- HUD: 算法信息 -->
        <div class="absolute top-4 right-4 text-blue-500 text-xs font-mono bg-black/60 px-2 py-1 rounded-none z-10 border border-blue-900/50">
          感知引擎: YOLOv10-M | {{ currentTime }}
        </div>
        
        <!-- HUD: AI 标注状态 -->
        <div class="absolute bottom-16 right-4 bg-blue-600/20 text-blue-400 text-[10px] font-bold px-2 py-1 border border-blue-500/30 z-10 uppercase tracking-widest backdrop-blur-sm">
          神经网络标注层已挂载
        </div>

        <div class="w-full h-full flex items-center justify-center bg-slate-950 relative overflow-hidden">
           <!-- 背景装饰：精密网格 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-0"></div>
          
           <!-- 画面特效：CRT 扫描线 -->
           <div class="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,255,0,0.03))] bg-[size:100%_4px,3px_100%] pointer-events-none z-20"></div>

          <!-- 核心：视频流加载 -->
          <div v-if="selectedCamera.streamUrl" class="w-full h-full flex items-center justify-center z-10">
              <!-- 此处直接通过 img 标签加载 MJPEG 流，由 Python AI 端实时生成 -->
              <img :src="selectedCamera.streamUrl" class="max-w-full max-h-full object-contain" alt="实时 AI 推理监控流" />
          </div>
          <div v-else class="text-center z-10">
              <Video class="w-16 h-16 mx-auto mb-4 opacity-20 text-slate-500" />
              <span class="text-xl font-mono text-slate-600 uppercase tracking-widest block">信号丢失 / NO SIGNAL</span>
              <p class="text-[10px] text-slate-700 mt-2 font-mono">设备源: {{ selectedCamera.name }}</p>
          </div>
        </div>

        <!-- 播放器悬浮控制条 -->
        <div class="absolute bottom-0 left-0 right-0 bg-slate-900/90 border-t border-slate-800 p-4 translate-y-full group-hover:translate-y-0 transition-transform duration-200">
          <div class="flex items-center justify-center space-x-4">
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
