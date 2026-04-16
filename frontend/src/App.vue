<script setup lang="ts">
import { onMounted } from 'vue';
import { startAlertVoiceListener } from './services/alertVoice';
import SimulationActionPopup from './components/SimulationActionPopup.vue';

onMounted(() => {
  startAlertVoiceListener();
});
</script>

<template>
  <div class="font-sans antialiased text-slate-900 bg-slate-50 min-h-screen">
    <router-view />
    <!-- 全局模拟动作弹窗：确保能在任何页面显示 AI 联动状态 -->
    <SimulationActionPopup />
  </div>
</template>
