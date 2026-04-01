<script setup lang="ts">
import { startAlertVoiceListener } from './services/alertVoice';

startAlertVoiceListener();
</script>

<template>
  <router-view />
</template>
