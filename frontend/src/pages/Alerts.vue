<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { AlertOctagon, Download, Filter, Info, RefreshCcw, Search } from 'lucide-vue-next';
import { apiService, type Alert } from '../api';
import { ALERT_RECEIVED_EVENT } from '../services/alertVoice';
import { cn } from '../utils';

const ALL_OPTION = '全部';
const riskLevels = [ALL_OPTION, 'Low', 'Medium', 'High', 'Critical'];

const filters = reactive({
  search: '',
  risk: ALL_OPTION,
  area: ALL_OPTION,
});

const allAlerts = ref<Alert[]>([]);
const loading = ref(false);

const availableAreas = computed(() => {
  const uniqueAreas = Array.from(new Set(allAlerts.value.map((alert) => alert.area).filter(Boolean)));
  return [ALL_OPTION, ...uniqueAreas];
});

const filteredAlerts = computed(() => {
  return allAlerts.value.filter((alert) => {
    const keyword = filters.search.trim().toLowerCase();
    const matchSearch = !keyword
      || alert.pigId.toLowerCase().includes(keyword)
      || alert.type.toLowerCase().includes(keyword);
    const matchRisk = filters.risk === ALL_OPTION || alert.risk === filters.risk;
    const matchArea = filters.area === ALL_OPTION || alert.area === filters.area;
    return matchSearch && matchRisk && matchArea;
  });
});

const summaryStats = computed(() => ({
  total: allAlerts.value.length,
  critical: allAlerts.value.filter((alert) => alert.risk === 'Critical').length,
  high: allAlerts.value.filter((alert) => alert.risk === 'High').length,
  medium: allAlerts.value.filter((alert) => alert.risk === 'Medium').length,
  low: allAlerts.value.filter((alert) => alert.risk === 'Low').length,
}));

async function loadAlerts() {
  loading.value = true;
  try {
    const response = await apiService.getAlerts();
    const payload = Array.isArray(response?.data) ? response.data : [];
    allAlerts.value = [...payload].sort((left, right) => Number(right.id) - Number(left.id));
  } catch (error) {
    console.error('Failed to load alerts:', error);
  } finally {
    loading.value = false;
  }
}

function handleRealtimeAlert(event: Event) {
  const incoming = (event as CustomEvent<Alert>).detail;
  if (!incoming) {
    return;
  }

  const nextAlerts = allAlerts.value.filter((alert) => alert.id !== incoming.id);
  nextAlerts.unshift(incoming);
  allAlerts.value = nextAlerts.sort((left, right) => Number(right.id) - Number(left.id));
}

function getRiskLabel(risk: string) {
  switch (risk) {
    case 'Critical':
      return '紧急';
    case 'High':
      return '高';
    case 'Medium':
      return '中';
    case 'Low':
      return '低';
    default:
      return risk;
  }
}

onMounted(() => {
  void loadAlerts();
  window.addEventListener(ALERT_RECEIVED_EVENT, handleRealtimeAlert as EventListener);
});

onBeforeUnmount(() => {
  window.removeEventListener(ALERT_RECEIVED_EVENT, handleRealtimeAlert as EventListener);
});
</script>

<template>
  <div class="space-y-6 flex flex-col h-full overflow-hidden">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-5">
      <div class="bg-white p-4 border border-slate-300 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">全部告警</span>
        <span class="text-3xl font-mono font-bold text-slate-900 mt-2">{{ summaryStats.total }}</span>
      </div>
      <div class="bg-red-50 p-4 border border-red-200 border-l-4 border-l-red-600 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-red-600 uppercase tracking-widest">紧急</span>
        <span class="text-3xl font-mono font-bold text-red-700 mt-2">{{ summaryStats.critical }}</span>
      </div>
      <div class="bg-orange-50 p-4 border border-orange-200 border-l-4 border-l-orange-600 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-orange-600 uppercase tracking-widest">高风险</span>
        <span class="text-3xl font-mono font-bold text-orange-700 mt-2">{{ summaryStats.high }}</span>
      </div>
      <div class="bg-yellow-50 p-4 border border-yellow-200 border-l-4 border-l-yellow-600 flex flex-col justify-between">
        <span class="text-[10px] font-bold text-yellow-600 uppercase tracking-widest">中风险</span>
        <span class="text-3xl font-mono font-bold text-yellow-700 mt-2">{{ summaryStats.medium }}</span>
      </div>
      <div class="bg-blue-50 p-4 border border-blue-200 border-l-4 border-l-blue-600 flex flex-col justify-between text-blue-700">
        <span class="text-[10px] font-bold text-blue-600 uppercase tracking-widest">低风险</span>
        <span class="text-3xl font-mono font-bold text-blue-800 mt-2">{{ summaryStats.low }}</span>
      </div>
    </div>

    <div class="bg-white border border-slate-300 flex flex-col flex-1 min-h-0 bg-[linear-gradient(rgba(0,0,0,0.01)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.01)_1px,transparent_1px)] bg-[size:32px_32px]">
      <div class="p-4 border-b border-slate-300 flex flex-col gap-4 bg-white/80 backdrop-blur-sm sticky top-0 z-20 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:flex-1">
          <div class="relative w-full lg:w-64 group">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 group-focus-within:text-blue-600" />
            <input
              v-model="filters.search"
              type="text"
              placeholder="搜索猪只 ID 或告警类型"
              class="w-full pl-9 pr-4 py-1.5 border border-slate-300 focus:outline-none focus:border-blue-600 font-mono text-xs placeholder-slate-400 bg-slate-50/50"
            />
          </div>

          <div class="hidden h-6 w-px bg-slate-300 lg:block"></div>

          <div class="flex items-center space-x-2">
            <Filter class="w-3.5 h-3.5 text-slate-500" />
            <select
              v-model="filters.area"
              class="pl-2 pr-8 py-1.5 border border-slate-300 bg-slate-50/50 font-mono text-[11px] font-bold appearance-none cursor-pointer"
            >
              <option v-for="area in availableAreas" :key="area" :value="area">{{ area }}</option>
            </select>
          </div>

          <div class="flex flex-wrap bg-slate-100 border border-slate-300 p-0.5">
            <button
              v-for="level in riskLevels"
              :key="level"
              @click="filters.risk = level"
              :class="cn(
                'px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-all',
                filters.risk === level
                  ? 'bg-white text-blue-700 shadow-sm border border-slate-200'
                  : 'text-slate-500 hover:text-slate-900 border border-transparent'
              )"
            >
              {{ level }}
            </button>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <button
            class="p-2 hover:bg-slate-100 border border-slate-300 text-slate-600"
            title="刷新"
            @click="loadAlerts"
          >
            <RefreshCcw :class="cn('w-4 h-4', loading && 'animate-spin')" />
          </button>
          <button class="p-2 hover:bg-slate-100 border border-slate-300 text-slate-400 cursor-not-allowed" title="导出功能待补充">
            <Download class="w-4 h-4" />
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-auto">
        <table class="w-full text-left border-collapse min-w-[800px]">
          <thead class="bg-slate-50 sticky top-0 z-10 text-slate-500 border-b border-slate-300">
            <tr>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">告警编号</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">猪只 ID</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">区域</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">异常类型</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em] border-r border-slate-200">风险等级</th>
              <th class="px-6 py-3 text-[10px] font-bold uppercase tracking-[0.2em]">时间</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 font-mono">
            <tr v-if="loading && filteredAlerts.length === 0">
              <td colspan="6" class="p-16 text-center text-slate-400 text-xs font-bold uppercase tracking-widest">
                LOADING_ALERTS
              </td>
            </tr>
            <tr v-else-if="filteredAlerts.length === 0">
              <td colspan="6" class="p-16 text-center text-slate-400 text-xs font-bold uppercase tracking-widest">
                NO_ALERT_MATCHED
              </td>
            </tr>
            <template v-for="alert in filteredAlerts" :key="alert.id">
              <tr class="hover:bg-slate-50 transition-colors cursor-pointer border-b-0">
                <td class="px-6 py-4 text-[11px] text-slate-400 border-r border-slate-100 italic">#{{ String(alert.id).padStart(4, '0') }}</td>
                <td class="px-6 py-4 border-r border-slate-100 font-bold text-slate-900 text-sm tracking-tighter">
                  <div class="flex items-center"><span class="w-1.5 h-1.5 bg-blue-600 mr-2"></span>{{ alert.pigId }}</div>
                </td>
                <td class="px-6 py-4 text-slate-600 border-r border-slate-100 text-[11px] font-bold uppercase">{{ alert.area }}</td>
                <td class="px-6 py-4 border-r border-slate-100 text-xs font-bold text-slate-800 tracking-tight">{{ alert.type }}</td>
                <td class="px-6 py-4 border-r border-slate-100 text-xs font-bold text-slate-800 tracking-tight font-mono">
                  <div
                    :class="cn(
                      'inline-flex items-center px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.1em] border-l-4 shadow-sm',
                      alert.risk === 'Critical' ? 'bg-red-950 text-red-100 border-l-red-500' :
                        alert.risk === 'High' ? 'bg-orange-900/10 text-orange-700 border-l-orange-500' :
                          alert.risk === 'Medium' ? 'bg-yellow-900/10 text-yellow-700 border-l-yellow-500' :
                            'bg-blue-900/10 text-blue-700 border-l-blue-500'
                    )"
                  >
                    <AlertOctagon v-if="alert.risk === 'Critical'" class="w-2.5 h-2.5 mr-1.5" />
                    {{ getRiskLabel(alert.risk) }}
                  </div>
                </td>
                <td class="px-6 py-4 text-slate-500 text-[10px] tabular-nums">{{ alert.timestamp }}</td>
              </tr>
              <tr v-if="alert.message" class="bg-slate-50/50">
                <td colspan="6" class="px-6 py-3 border-t border-slate-100 text-xs text-slate-600 leading-relaxed font-sans">
                  <div class="flex items-start">
                    <span class="font-bold text-slate-400 mr-2 shrink-0">诊断说明:</span>
                    <span>{{ alert.message }}</span>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="px-4 py-2 border-t border-slate-300 bg-slate-50 flex flex-col gap-2 text-[9px] text-slate-400 font-bold uppercase tracking-widest sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center">
          <Info class="w-3 h-3 mr-2" />
          {{ loading ? '告警列表同步中' : '实时告警已接入自动播报' }}
        </div>
        <div class="font-mono">TOTAL: {{ filteredAlerts.length }} ALERTS</div>
      </div>
    </div>
  </div>
</template>
