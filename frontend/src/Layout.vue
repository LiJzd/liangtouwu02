<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
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
const isMobileMenuOpen = ref(false);

function handleNavigate(path: string) {
  void router.push(path);
}
</script>

<template>
  <div class="flex flex-col min-h-[100dvh]">
    <!-- Top-Only Navigation Header -->
    <header class="fixed top-0 w-full z-50 bg-white/95 backdrop-blur-md flex justify-between items-center px-8 h-16 border-b border-emerald-200">
      <!-- Left: Logo, Title & Hamburger for Mobile -->
      <div class="flex items-center gap-4 shrink-0">
        <!-- Hamburger Button for small/medium viewports -->
        <button @click="isMobileMenuOpen = true" class="flex lg:hidden items-center justify-center p-2 rounded-xl text-emerald-900 hover:bg-emerald-50 transition-colors border-none outline-none cursor-pointer">
          <span class="material-symbols-outlined text-xl">menu</span>
        </button>
        
        <img alt="掌上明猪" class="h-8 object-contain" src="/logo.png"/>
        <div class="h-5 w-[1px] bg-emerald-300"></div>
        <h2 class="font-headline text-base font-bold text-emerald-900">两头乌智能养殖</h2>
      </div>

      <!-- Center: Main Navigation Menu (Horizontal Flow for Large Screens) -->
      <nav class="hidden lg:flex items-center gap-2.5 font-headline text-xs font-bold my-auto relative">
        <template v-for="item in navItems" :key="item.id">
          <router-link
            :to="item.path"
            :class="[
              'transition-all duration-300 py-1.5 px-3 rounded-xl flex items-center gap-1.5 border border-transparent hover:scale-105 active:scale-95',
              currentPath === item.path
                ? 'text-secondary bg-emerald-100/50 font-semibold'
                : 'text-on-surface-variant hover:text-secondary hover:bg-emerald-50/30 font-medium'
            ]"
          >
            <span class="material-symbols-outlined text-[15px]">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </router-link>
        </template>
      </nav>

      <!-- Right: SSE Status and Utility Action Icons -->
      <div class="flex items-center gap-4 pl-4 shrink-0">
        <!-- SSE status badge -->
        <div class="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50/50 border border-emerald-100">
          <div :class="['w-1.5 h-1.5 rounded-full', alertVoiceState.connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-rose-500 animate-pulse']"></div>
          <span class="text-[10px] font-bold uppercase tracking-wider" :class="alertVoiceState.connected ? 'text-emerald-700' : 'text-rose-600'">
            {{ alertVoiceState.connected ? '链路正常' : '正在连接...' }}
          </span>
        </div>

        <div class="flex items-center gap-4 border-l border-emerald-200 pl-4 text-on-surface-variant">
          <span class="material-symbols-outlined text-sm cursor-pointer hover:text-secondary">sensors</span>
          <span class="material-symbols-outlined text-sm cursor-pointer hover:text-secondary">notifications</span>
        </div>
      </div>
    </header>

    <!-- Mobile Navigation Drawer Overlay -->
    <Transition name="fade">
      <div v-if="isMobileMenuOpen" @click="isMobileMenuOpen = false" class="fixed inset-0 bg-slate-950/20 backdrop-blur-sm z-50 lg:hidden"></div>
    </Transition>

    <!-- Mobile Navigation Drawer -->
    <Transition name="drawer">
      <div v-if="isMobileMenuOpen" class="fixed inset-y-0 left-0 w-64 z-50 bg-[#fafcfc]/95 backdrop-blur-xl rounded-r-2xl border-r border-emerald-100 shadow-[0_8px_32px_rgba(6,78,59,0.08)] flex flex-col p-6 lg:hidden">
        <!-- Drawer Header -->
        <div class="flex justify-between items-center mb-8">
          <div class="flex items-center gap-2">
            <img alt="掌上明猪" class="h-6 object-contain" src="/logo.png"/>
            <h2 class="font-headline text-xs font-bold text-emerald-900">智能养殖中枢</h2>
          </div>
          <button @click="isMobileMenuOpen = false" class="flex items-center justify-center p-1.5 rounded-full text-emerald-900 hover:bg-emerald-50 border-none outline-none cursor-pointer">
            <span class="material-symbols-outlined text-sm">close</span>
          </button>
        </div>

        <!-- Drawer Links -->
        <nav class="flex-1 space-y-2">
          <template v-for="item in navItems" :key="item.id">
            <button
              @click="handleNavigate(item.path); isMobileMenuOpen = false"
              :class="[
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-300 border-none outline-none cursor-pointer',
                currentPath === item.path
                  ? 'text-secondary bg-emerald-100/50 font-semibold'
                  : 'text-on-surface-variant hover:text-secondary hover:bg-emerald-50/50 font-medium'
              ]"
            >
              <span class="material-symbols-outlined text-base">{{ item.icon }}</span>
              <span class="text-xs">{{ item.label }}</span>
            </button>
          </template>
        </nav>

        <!-- SSE Indicator in Drawer -->
        <div class="mt-auto pt-4 border-t border-emerald-100/30">
          <div class="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-emerald-50/50 border border-emerald-100/60">
            <div :class="['w-1.5 h-1.5 rounded-full', alertVoiceState.connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-rose-500 animate-pulse']"></div>
            <span class="text-[9px] font-bold tracking-wider" :class="alertVoiceState.connected ? 'text-emerald-700' : 'text-rose-600'">
              {{ alertVoiceState.connected ? '实时链路正常' : '连接断开' }}
            </span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Main Viewport (Sidebar completely killed, pl-0 for full widescreen layout) -->
    <main class="pt-16 flex-1 w-full bg-transparent mx-auto relative z-10 transition-all duration-500">
      <router-view />
    </main>

    <!-- Upload Anomaly Floating Action Button -->
    <div class="fixed bottom-8 right-8 z-50">
      <button class="group flex items-center gap-3 bg-secondary text-white px-6 py-4 rounded-full font-headline font-bold shadow-2xl shadow-secondary/40 hover:scale-105 active:scale-95 transition-all border-none">
        <span class="material-symbols-outlined">add</span>
        <span class="max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-500 whitespace-nowrap">上报异常项</span>
      </button>
    </div>

    <!-- AI Auto-Action Simulation Popup -->
    <SimulationActionPopup />
  </div>
</template>

<style scoped>
/* Fade Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Drawer Transition */
.drawer-enter-active,
.drawer-leave-active {
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(-100%);
}

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
</style>
