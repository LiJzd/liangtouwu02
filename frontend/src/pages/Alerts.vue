<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
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
const selectedIds = ref<(number | string)[]>([]);

const isAllSelected = computed(() => {
  return filteredAlerts.value.length > 0 && selectedIds.value.length === filteredAlerts.value.length;
});

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = [];
  } else {
    selectedIds.value = filteredAlerts.value.map(a => a.id);
  }
}

function toggleSelect(id: number | string) {
  const index = selectedIds.value.indexOf(id);
  if (index > -1) {
    selectedIds.value.splice(index, 1);
  } else {
    selectedIds.value.push(id);
  }
}

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
    
    // === 补偿由于后端或API过滤规则导致丢失的模拟报警事件 ===
    const rawCache = window.sessionStorage.getItem('liangtouwu-pigbot-alert-cache');
    const cachedSimulatedAlerts: Alert[] = [];
    if (rawCache) {
      try {
        const parsed = JSON.parse(rawCache);
        if (Array.isArray(parsed)) {
          parsed.forEach((item: any) => {
            if (item && item.alert) {
              // 为了确保所有通过接口实触发的告警（即便是未显式包含“模拟”字样）
              // 都能在通过刷新或页面加载时恢复，我们放宽限制，将所有缓存事件均纳入补偿
              cachedSimulatedAlerts.push(item.alert);
            }
          });
        }
      } catch (e) {
        console.error('解析本地告警缓存失败', e);
      }
    }

    const mergedMap = new Map<number | string, Alert>();
    payload.forEach((a) => mergedMap.set(a.id, a));
    cachedSimulatedAlerts.forEach((a) => {
      if (!mergedMap.has(a.id)) {
        mergedMap.set(a.id, a);
      }
    });

    allAlerts.value = Array.from(mergedMap.values()).sort((left, right) => Number(right.id) - Number(left.id));
  } catch (error) {
    console.error('Failed to load alerts:', error);
  } finally {
    loading.value = false;
  }
}

function handleRealtimeAlert(event: Event) {
  const incoming = (event as CustomEvent<Alert>).detail;
  console.log('[AlertsPage] 实时监听到告警事件推送:', incoming);
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

async function onDeleteAlert(id: number | string) {
  if (!window.confirm('确定要删除这条告警记录吗？此操作不可撤销。')) {
    return;
  }
  
  try {
    const res = await apiService.deleteAlert(id);
    if (res.code === 200) {
      allAlerts.value = allAlerts.value.filter(a => a.id !== id);
      selectedIds.value = selectedIds.value.filter(sid => sid !== id);
    } else {
      alert(res.message || '删除失败');
    }
  } catch (error) {
    console.error('Delete alert failed:', error);
    alert('请求失败，请稍后重试');
  }
}

async function onBatchDelete() {
  if (selectedIds.value.length === 0) return;
  if (!window.confirm(`确定要删除选中的 ${selectedIds.value.length} 条告警记录吗？`)) {
    return;
  }

  try {
    const res = await apiService.deleteAlertsBatch(selectedIds.value);
    if (res.code === 200) {
      const idsToRemove = new Set(selectedIds.value);
      allAlerts.value = allAlerts.value.filter(a => !idsToRemove.has(a.id));
      selectedIds.value = [];
    } else {
      alert(res.message || '批量删除失败');
    }
  } catch (error) {
    console.error('Batch delete failed:', error);
    alert('请求失败');
  }
}

async function onClearAll() {
  if (!window.confirm('警告：确定要清空所有告警记录吗？此操作将删除数据库中的所有告警数据！')) {
    return;
  }

  try {
    const res = await apiService.clearAllAlerts();
    if (res.code === 200) {
      allAlerts.value = [];
      selectedIds.value = [];
    } else {
      alert(res.message || '清空失败');
    }
  } catch (error) {
    console.error('Clear all failed:', error);
    alert('请求失败');
  }
}


onMounted(() => {
  void loadAlerts();
  // 主要告警监听
  window.addEventListener(ALERT_RECEIVED_EVENT, handleRealtimeAlert as EventListener);
});

onBeforeUnmount(() => {
  window.removeEventListener(ALERT_RECEIVED_EVENT, handleRealtimeAlert as EventListener);
});
</script>

<template>
  <div class="space-y-6 flex flex-col h-full overflow-hidden">
    <!-- 顶部状态卡片 -->
    <div class="grid grid-cols-1 gap-6 md:grid-cols-5">
      <div class="bg-white/95 p-5 rounded-2xl border border-emerald-200 shadow-sm flex flex-col justify-between hover:-translate-y-1 transition duration-300">
        <span class="text-[10px] font-bold text-emerald-900/60 uppercase tracking-widest">全部告警</span>
        <span class="text-4xl font-headline font-bold text-emerald-950 mt-2">{{ summaryStats.total }}</span>
      </div>
      <div class="bg-red-50/90 p-5 rounded-2xl border border-red-200 shadow-sm flex flex-col justify-between hover:-translate-y-1 transition duration-300">
        <span class="text-[10px] font-bold text-red-600 uppercase tracking-widest">紧急</span>
        <span class="text-4xl font-headline font-bold text-red-700 mt-2">{{ summaryStats.critical }}</span>
      </div>
      <div class="bg-orange-50/90 p-5 rounded-2xl border border-orange-200 shadow-sm flex flex-col justify-between hover:-translate-y-1 transition duration-300">
        <span class="text-[10px] font-bold text-orange-600 uppercase tracking-widest">高风险</span>
        <span class="text-4xl font-headline font-bold text-orange-700 mt-2">{{ summaryStats.high }}</span>
      </div>
      <div class="bg-amber-50/90 p-5 rounded-2xl border border-amber-200 shadow-sm flex flex-col justify-between hover:-translate-y-1 transition duration-300">
        <span class="text-[10px] font-bold text-amber-600 uppercase tracking-widest">中风险</span>
        <span class="text-4xl font-headline font-bold text-amber-700 mt-2">{{ summaryStats.medium }}</span>
      </div>
      <div class="bg-blue-50/90 p-5 rounded-2xl border border-blue-200 shadow-sm flex flex-col justify-between hover:-translate-y-1 transition duration-300">
        <span class="text-[10px] font-bold text-blue-600 uppercase tracking-widest">低风险</span>
        <span class="text-4xl font-headline font-bold text-blue-800 mt-2">{{ summaryStats.low }}</span>
      </div>
    </div>

    <!-- 列表主体 -->
    <div class="bg-white/90 backdrop-blur-md rounded-2xl border border-emerald-200 shadow-sm flex flex-col flex-1 min-h-[500px]">
      
      <!-- 控制栏 -->
      <div class="p-4 border-b border-emerald-100 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:flex-1">
          <div class="relative w-full lg:w-64 group">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-lg text-emerald-900/40 group-focus-within:text-secondary transition-colors">search</span>
            <input
              v-model="filters.search"
              type="text"
              placeholder="搜索猪只 ID 或类型"
              class="w-full pl-10 pr-4 py-2 border border-emerald-200 rounded-xl focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary font-inter text-sm placeholder-emerald-900/30 bg-white/50 transition-all"
            />
          </div>

          <div class="hidden h-6 w-px bg-emerald-200 lg:block"></div>

          <div class="flex items-center space-x-2 relative">
            <span class="material-symbols-outlined text-lg text-emerald-900/60 absolute left-3 pointer-events-none">filter_alt</span>
            <select
              v-model="filters.area"
              class="pl-9 pr-8 py-2 border border-emerald-200 rounded-xl bg-white/50 text-emerald-900 text-sm font-semibold appearance-none cursor-pointer focus:outline-none focus:border-secondary"
            >
              <option v-for="area in availableAreas" :key="area" :value="area">{{ area }}</option>
            </select>
            <span class="material-symbols-outlined absolute right-3 pointer-events-none text-emerald-900/40">expand_more</span>
          </div>

          <div class="flex gap-1 bg-emerald-50/80 p-1 rounded-xl border border-emerald-100">
            <button
              v-for="level in riskLevels"
              :key="level"
              @click="filters.risk = level"
              :class="cn(
                'px-4 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg transition-all',
                filters.risk === level
                  ? 'bg-white text-secondary shadow-sm'
                  : 'text-emerald-900/60 hover:text-emerald-900 hover:bg-emerald-100/50'
              )"
            >
              {{ level }}
            </button>
          </div>
        </div>

        <div class="flex items-center space-x-2">

          <button
            v-if="selectedIds.length > 0"
            @click="onBatchDelete"
            class="flex items-center gap-1.5 px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded-xl hover:bg-red-100 transition-all text-xs font-bold"
          >
            <span class="material-symbols-outlined text-[18px]">delete_sweep</span>
            批量删除 ({{ selectedIds.length }})
          </button>
          
          <button
            @click="onClearAll"
            class="flex items-center gap-1.5 px-4 py-2 bg-white text-emerald-900/60 border border-emerald-200 rounded-xl hover:text-red-600 hover:border-red-200 transition-all text-xs font-bold"
          >
            <span class="material-symbols-outlined text-[18px]">clear_all</span>
            清空列表
          </button>

          <div class="w-px h-6 bg-emerald-100 mx-1"></div>

          <button
            class="flex items-center justify-center w-10 h-10 rounded-xl bg-white border border-emerald-200 text-emerald-900/60 hover:text-secondary hover:border-secondary transition-all"
            title="刷新"
            @click="loadAlerts"
          >
            <span :class="cn('material-symbols-outlined text-[20px]', loading && 'animate-spin')">refresh</span>
          </button>
        </div>
      </div>

      <!-- 表格区 -->
      <div class="flex-1 overflow-auto rounded-b-2xl">
        <table class="w-full text-left border-collapse min-w-[800px]">
          <thead class="bg-surface-container-highest sticky top-0 z-10 text-emerald-900 border-b border-emerald-200">
            <tr>
              <th class="px-6 py-4 w-12">
                <div 
                  @click="toggleSelectAll"
                  class="w-5 h-5 rounded border-2 border-emerald-200 flex items-center justify-center cursor-pointer transition-colors"
                  :class="isAllSelected ? 'bg-secondary border-secondary' : 'bg-white'"
                >
                  <span v-if="isAllSelected" class="material-symbols-outlined text-white text-[16px]">check</span>
                </div>
              </th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest">告警编号</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest">猪只 ID</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest">区域</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest">异常类型</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest">风险等级</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest">时间</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-right">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-emerald-100/50">
            <tr v-if="loading && filteredAlerts.length === 0">
              <td colspan="7" class="p-16 text-center text-emerald-900/40 text-xs font-bold uppercase tracking-widest">
                LOADING_ALERTS
              </td>
            </tr>
            <tr v-else-if="filteredAlerts.length === 0">
              <td colspan="7" class="p-16 text-center text-emerald-900/40 text-xs font-bold uppercase tracking-widest">
                NO_ALERT_MATCHED
              </td>
            </tr>
            <template v-for="alert in filteredAlerts" :key="alert.id">
              <tr 
                class="hover:bg-emerald-50/50 transition-colors cursor-pointer border-b-0 group"
                :class="selectedIds.includes(alert.id) && 'bg-emerald-50/80'"
              >
                <td class="px-6 py-4" @click.stop="toggleSelect(alert.id)">
                  <div 
                    class="w-5 h-5 rounded border-2 border-emerald-200 flex items-center justify-center cursor-pointer transition-colors"
                    :class="selectedIds.includes(alert.id) ? 'bg-secondary border-secondary' : 'bg-white group-hover:border-secondary/50'"
                  >
                    <span v-if="selectedIds.includes(alert.id)" class="material-symbols-outlined text-white text-[16px]">check</span>
                  </div>
                </td>
                <td class="px-6 py-4 text-xs text-emerald-900/40 font-headline italic">#{{ String(alert.id).padStart(4, '0') }}</td>
                <td class="px-6 py-4 font-bold text-emerald-950 text-sm tracking-tight font-headline">
                  <div class="flex items-center"><span class="w-1.5 h-1.5 rounded-full bg-secondary mr-2"></span>{{ alert.pigId }}</div>
                </td>
                <td class="px-6 py-4 text-emerald-900/80 text-xs font-bold">{{ alert.area }}</td>
                <td class="px-6 py-4 text-xs font-bold text-emerald-950 tracking-tight">{{ alert.type }}</td>
                <td class="px-6 py-4 text-xs font-bold tracking-tight">
                  <div
                    :class="cn(
                      'inline-flex items-center px-2.5 py-1 text-[10px] font-black uppercase tracking-widest rounded-full',
                      alert.risk === 'Critical' ? 'bg-red-100 text-red-700 border border-red-200' :
                        alert.risk === 'High' ? 'bg-orange-100 text-orange-700 border border-orange-200' :
                          alert.risk === 'Medium' ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                            'bg-blue-100 text-blue-700 border border-blue-200'
                    )"
                  >
                    <span v-if="alert.risk === 'Critical'" class="material-symbols-outlined text-[12px] mr-1">error</span>
                    {{ getRiskLabel(alert.risk) }}
                  </div>
                </td>
                <td class="px-6 py-4 text-emerald-900/60 text-[10px] font-mono">{{ alert.timestamp }}</td>
                <td class="px-6 py-4 text-right">
                  <button 
                    @click.stop="onDeleteAlert(alert.id)"
                    class="p-2 text-emerald-900/40 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all opacity-40 group-hover:opacity-100"
                    title="删除告警"
                  >
                    <span class="material-symbols-outlined text-[18px]">delete</span>
                  </button>
                </td>
              </tr>
              <tr v-if="alert.message" class="bg-surface-bright/50">
                <td colspan="7" class="px-6 py-4 border-t border-emerald-50 text-xs text-emerald-900/80 leading-relaxed font-inter">
                  <div class="flex items-start">
                    <span class="material-symbols-outlined text-[16px] text-emerald-900/40 mr-2 shrink-0">info</span>
                    <span class="flex-1">{{ alert.message }}</span>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- 底部统计栏 -->
      <div class="px-6 py-3 border-t border-emerald-200 bg-surface-container-low rounded-b-2xl flex flex-col gap-2 text-[10px] text-emerald-900/60 font-bold uppercase tracking-widest sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center">
          <span class="material-symbols-outlined text-[14px] mr-2">wifi_tethering</span>
          {{ loading ? '告警列表同步中' : '系统监控中 - 实时告警已接入自动播报' }}
        </div>
        <div class="font-headline tracking-widest">TOTAL: {{ filteredAlerts.length }} ALERTS</div>
      </div>
    </div>
  </div>
</template>
