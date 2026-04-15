<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { cn } from './utils';
import SimulationActionPopup from './components/SimulationActionPopup.vue';
import { alertVoiceState } from './services/alertVoice';

const router = useRouter();
const route = useRoute();

const navItems = [
  { id: 'dashboard', label: '总览看板', icon: 'dashboard', path: '/dashboard' },
  { id: 'monitor', label: '视频监控', icon: 'videocam', path: '/monitor' },
  { id: 'growth-curve', label: '生长曲线', icon: 'trending_up', path: '/growth-curve' },
  { id: 'daily-briefing', label: '每日报告', icon: 'analytics', path: '/daily-briefing' },
  { id: 'alerts', label: '告警中心', icon: 'warning', path: '/alerts' },
  { id: 'remote-control', label: '远程控制', icon: 'settings_remote', path: '/remote-control' },
  { id: 'pig-bot', label: '猪BOT助手', icon: 'smart_toy', path: '/pig-bot' },
];

const currentPath = computed(() => route.path);

function isItemActive(item: { id: string; path: string }) {
  return item.path === currentPath.value;
}

function handleNavigate(path: string) {
  void router.push(path);
}
</script>

<template>
  <div class="flex flex-col min-h-[100dvh]">
    <header class="fixed top-0 w-full z-50 bg-white/90 backdrop-blur-md flex justify-between items-center px-8 h-14 border-b border-emerald-200">
      <div class="flex items-center gap-4">
        <img alt="掌上明猪" class="h-8 object-contain" src="/logo.png"/>
        <div class="h-5 w-[1px] bg-emerald-300"></div>
        <h2 class="font-headline text-base font-bold text-emerald-900">两头乌智能养殖</h2>
      </div>
      <div class="hidden md:flex items-center gap-8">
        <nav class="flex items-center gap-6 font-headline text-xs font-bold">
          <router-link to="/dashboard" :class="currentPath === '/dashboard' ? 'text-secondary' : 'text-on-surface-variant hover:text-secondary transition-colors'">生猪遥测</router-link>
          <router-link to="/monitor" :class="currentPath === '/monitor' ? 'text-secondary' : 'text-on-surface-variant hover:text-secondary transition-colors'">场域分析</router-link>
          <router-link to="/alerts" :class="currentPath === '/alerts' ? 'text-secondary' : 'text-on-surface-variant hover:text-secondary transition-colors'">环境告警</router-link>
        </nav>
        <div class="flex items-center gap-4 border-l border-emerald-200 pl-6">
          <span class="material-symbols-outlined text-on-surface-variant text-sm cursor-pointer hover:text-secondary">sensors</span>
          <span class="material-symbols-outlined text-on-surface-variant text-sm cursor-pointer hover:text-secondary">notifications</span>
        </div>
      </div>
    </header>

    <aside class="fixed left-0 h-full w-60 border-r border-emerald-200 bg-white/80 backdrop-blur-xl flex flex-col pt-24 pb-8 px-4 z-40 hidden md:flex">
      <div class="mb-6 px-2">
        <h2 class="font-headline text-emerald-900 font-bold text-base">扇区监控</h2>
        <p class="text-on-surface-variant/80 text-[9px] font-bold uppercase tracking-widest">活跃数据流: 1,248</p>
      </div>
      
      <nav class="flex-1 space-y-1">
        <template v-for="item in navItems" :key="item.id">
          <button
            @click="handleNavigate(item.path)"
            :class="cn(
              'w-full flex items-center gap-3 px-3 py-2 font-inter text-sm transition-all duration-300 text-left outline-none',
              isItemActive(item) 
                ? 'text-secondary bg-emerald-100/50 border-r-2 border-secondary font-semibold' 
                : 'text-on-surface-variant hover:text-secondary hover:bg-emerald-50 font-medium'
            )"
          >
            <span class="material-symbols-outlined text-lg">{{ item.icon }}</span>
            <span class="flex-1">{{ item.label }}</span>
          </button>
        </template>
      </nav>
      
      <!-- SSE 状态指示器 -->
      <div class="px-3 py-2 mb-2">
        <div class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-emerald-50/50 border border-emerald-100">
          <div :class="['w-1.5 h-1.5 rounded-full', alertVoiceState.connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-rose-500 animate-pulse']"></div>
          <span class="text-[10px] font-bold uppercase tracking-wider" :class="alertVoiceState.connected ? 'text-emerald-700' : 'text-rose-600'">
            {{ alertVoiceState.connected ? '实时链路正常' : '正在建立链路...' }}
          </span>
        </div>
      </div>
      
      <div class="mt-auto space-y-1">
          <a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant/80 hover:text-secondary font-inter text-xs font-medium" href="#">
            <span class="material-symbols-outlined text-sm">memory</span>
            <span>系统诊断</span>
          </a>
          <a class="flex items-center gap-3 px-3 py-2 text-on-surface-variant/80 hover:text-secondary font-inter text-xs font-medium" href="#">
            <span class="material-symbols-outlined text-sm">admin_panel_settings</span>
            <span>后台管理</span>
          </a>
        </div>
    </aside>

    <main class="md:pl-60 pt-14 flex-1 w-full bg-transparent mx-auto relative z-10 transition-all duration-500">
      <router-view />
    </main>

    <div class="fixed bottom-8 right-8 z-50">
      <button class="group flex items-center gap-3 bg-secondary text-white px-6 py-4 rounded-full font-headline font-bold shadow-2xl shadow-secondary/40 hover:scale-105 active:scale-95 transition-all border-none">
        <span class="material-symbols-outlined">add</span>
        <span class="max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-500 whitespace-nowrap">上报异常项</span>
      </button>
    </div>

    <!-- AI 自动处置弹窗 -->
    <SimulationActionPopup />
  </div>
</template>
