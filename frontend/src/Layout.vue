<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  AlertTriangle,
  LayoutDashboard,
  Menu,
  MonitorPlay,
  PiggyBank,
  TrendingUp,
  Warehouse,
  MessageSquare,
} from 'lucide-vue-next';
import { cn } from './utils';

const router = useRouter();
const route = useRoute();

const isSidebarOpen = ref(false);

const navItems = [
  { id: 'dashboard', label: '总览看板', icon: LayoutDashboard, path: '/dashboard' },
  { id: 'monitor', label: '视频监控', icon: MonitorPlay, path: '/monitor' },
  { id: 'growth-curve', label: '生长曲线', icon: TrendingUp, path: '/growth-curve' },
  { id: 'daily-briefing', label: '每日报告', icon: Warehouse, path: '/daily-briefing' },
  { id: 'alerts', label: '告警中心', icon: AlertTriangle, path: '/alerts' },
  { id: 'pig-bot', label: '猪BOT助手', icon: MessageSquare, path: '/pig-bot' },
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
  <div class="min-h-screen bg-[#f1f2f6] flex font-sans text-slate-800">
    <div
      class="fixed top-8 left-8 z-40 bg-white/60 backdrop-blur-md p-3 rounded-2xl shadow-sm cursor-pointer hover:bg-white hover:shadow-md transition-all duration-300 pointer-events-auto"
      @mouseenter="isSidebarOpen = true"
    >
      <Menu class="w-6 h-6 text-slate-700" />
    </div>

    <div
      :class="cn(
        'w-64 h-screen bg-white/90 backdrop-blur-2xl fixed left-0 top-0 flex flex-col z-50 transition-all duration-500 shadow-[20px_0_60px_rgba(0,0,0,0.05)] overflow-hidden',
        isSidebarOpen ? 'translate-x-0 opacity-100' : '-translate-x-full opacity-0 pointer-events-none'
      )"
      @mouseleave="isSidebarOpen = false"
    >
      <div class="h-24 flex items-center px-8 flex-shrink-0 mt-4">
        <PiggyBank class="w-8 h-8 text-[#0f172a] mr-3" />
        <h1 class="text-2xl font-black text-[#0f172a] tracking-tight">两头乌</h1>
      </div>

      <nav class="flex-1 px-4 space-y-1 overflow-y-auto pb-6">
        <div v-for="item in navItems" :key="item.id">
          <button
            @click="handleNavigate(item.path)"
            :class="cn(
              'w-full flex items-center px-4 py-3 rounded-2xl transition-all duration-300 group',
              isItemActive(item)
                ? 'bg-blue-50/80 shadow-sm text-blue-700 font-bold'
                : 'text-slate-500 hover:text-black hover:bg-slate-100/50 font-medium'
            )"
          >
            <component
              :is="item.icon"
              :class="cn(
                'w-5 h-5 mr-4 transition-colors',
                isItemActive(item) ? 'text-blue-700' : 'text-slate-400 group-hover:text-black'
              )"
            />
            <span class="flex-1 text-sm text-left">{{ item.label }}</span>
          </button>
        </div>
      </nav>
    </div>

    <div class="flex-1 flex flex-col px-4 md:px-8 pt-6 pb-8 transition-all duration-500 w-full">
      <main class="flex-1 bg-transparent rounded-[2rem] relative z-10 w-full mx-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>
