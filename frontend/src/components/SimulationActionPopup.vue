<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { SIMULATION_ACTION_EVENT } from '../services/alertVoice';

interface ActionDetail {
  action: string;
  icon: string;
  target: string;
}

const isVisible = ref(false);
const detail = ref<ActionDetail | null>(null);
let timer: number | null = null;

function handleAction(event: Event) {
  const data = (event as CustomEvent<ActionDetail>).detail;
  detail.value = data;
  isVisible.value = true;
  
  if (timer) window.clearTimeout(timer);
  timer = window.setTimeout(() => {
    isVisible.value = false;
  }, 6000);
}

onMounted(() => {
  window.addEventListener(SIMULATION_ACTION_EVENT, handleAction as EventListener);
});

onBeforeUnmount(() => {
  window.removeEventListener(SIMULATION_ACTION_EVENT, handleAction as EventListener);
});
</script>

<template>
  <Transition
    enter-active-class="transition duration-500 ease-out"
    enter-from-class="transform translate-y-10 opacity-0 scale-95"
    enter-to-class="transform translate-y-0 opacity-100 scale-100"
    leave-active-class="transition duration-300 ease-in"
    leave-from-class="transform translate-y-0 opacity-100 scale-100"
    leave-to-class="transform translate-y-4 opacity-0 scale-95"
  >
    <div v-if="isVisible && detail" class="fixed bottom-24 right-8 z-[100] w-80">
      <div class="bg-emerald-950/80 backdrop-blur-xl border border-emerald-400/30 rounded-2xl p-4 shadow-2xl flex items-center gap-4 overflow-hidden relative">
        <!-- 装饰性光效 -->
        <div class="absolute -top-10 -right-10 w-24 h-24 bg-secondary/20 blur-3xl rounded-full"></div>
        
        <div class="relative">
          <div class="w-12 h-12 bg-secondary/10 rounded-xl flex items-center justify-center border border-secondary/20">
            <span v-if="detail" class="material-symbols-outlined text-secondary text-3xl animate-spin-slow">
              {{ 
                detail.icon === 'fan' ? 'mode_fan' : 
                detail.icon === 'medical' ? 'medical_services' :
                detail.icon === 'brain' ? 'psychology' :
                'settings' 
              }}
            </span>
          </div>
          <!-- 动作点动画 -->
          <div class="absolute -top-1 -right-1 w-3 h-3 bg-secondary rounded-full border-2 border-emerald-900 animate-ping"></div>
        </div>
        
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-[10px] font-bold text-secondary uppercase tracking-widest">AI 自动处置</span>
            <div class="h-px flex-1 bg-secondary/20"></div>
          </div>
          <h3 class="text-white font-headline font-bold text-sm leading-tight">
            {{ detail.action }}
          </h3>
          <p class="text-emerald-300/60 text-[10px] font-medium mt-1 uppercase tracking-tight">
            位置: {{ detail.target }}
          </p>
        </div>

        <button @click="isVisible = false" class="text-white/20 hover:text-white transition-colors">
          <span class="material-symbols-outlined text-sm">close</span>
        </button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.animate-spin-slow {
  animation: spin 3s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
