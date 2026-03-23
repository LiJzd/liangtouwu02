<script setup lang="ts">
/**
 * 全局工作台布局 (Layout) - 现代化流体渐变风格
 */
import { ref, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { 
  ChevronDown, 
  ChevronRight,
  Warehouse, 
  LayoutDashboard, 
  MonitorPlay, 
  Activity, 
  AlertTriangle,
  Menu,
  TrendingUp,
  Settings,
  PiggyBank
} from 'lucide-vue-next';
import { cn } from './utils';

const router = useRouter();
const route = useRoute();

const expandedItems = ref<string[]>(['analysis']);
const isSidebarOpen = ref(false);

const NAV_ITEMS = [
  { id: 'dashboard', label: '仪表板', icon: LayoutDashboard, path: '/dashboard' },
  { id: 'analysis', label: '分析', icon: Activity, path: '/analysis', children: [
      { id: 'analysis', label: '全域横向对比', path: '/analysis' },
      { id: 'analysis-area-a', label: '猪舍 A 区趋势', path: '/analysis?area=猪舍 A 区' }, 
  ] },
  { id: 'monitor', label: '实时监控', icon: MonitorPlay, path: '/monitor' },
  { id: 'growth-curve', label: '生长预测', icon: TrendingUp, path: '/growth-curve' },
  { id: 'daily-briefing', label: '每日简报', icon: Warehouse, path: '/daily-briefing' },
  { id: 'alerts', label: '警报', icon: AlertTriangle, path: '/alerts' },
  { id: 'settings', label: '设置', icon: Settings, path: '/settings' },
];

const currentPath = computed(() => route.path);
const currentQueryArea = computed(() => route.query.area);

const isItemActive = (item: any) => {
  if (item.path === currentPath.value) {
      if (item.id === 'analysis' && !currentQueryArea.value) return true;
      return true;
  }
  if (item.children) {
      return item.children.some((child: any) => isChildActive(child));
  }
  return false;
};

const isChildActive = (child: any) => {
    if (child.path.includes('?')) {
        const [path, query] = child.path.split('?');
        const params = new URLSearchParams(query);
        return currentPath.value === path && currentQueryArea.value === params.get('area');
    }
    return child.path === currentPath.value;
}

const toggleExpand = (id: string) => {
  if (expandedItems.value.includes(id)) {
    expandedItems.value = expandedItems.value.filter(i => i !== id);
  } else {
    expandedItems.value.push(id);
  }
};

const handleNavigate = (path: string) => router.push(path);
</script>

<template>
  <div class="min-h-screen bg-[#f1f2f6] flex font-sans text-slate-800">
    <!-- 悬浮触发按钮 -->
    <div 
       class="fixed top-8 left-8 z-40 bg-white/60 backdrop-blur-md p-3 rounded-2xl shadow-sm cursor-pointer hover:bg-white hover:shadow-md transition-all duration-300 pointer-events-auto"
       @mouseenter="isSidebarOpen = true"
    >
       <Menu class="w-6 h-6 text-slate-700" />
    </div>

    <!-- 固定侧边栏 (隐形悬浮伸缩) -->
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
        <div v-for="item in NAV_ITEMS" :key="item.id">
            <button
                @click="item.children ? toggleExpand(item.id) : handleNavigate(item.path)"
                :class="cn(
                  'w-full flex items-center px-4 py-3 rounded-2xl transition-all duration-300 group',
                  isItemActive(item)
                    ? 'bg-blue-50/80 shadow-sm text-blue-700 font-bold' 
                    : 'text-slate-500 hover:text-black hover:bg-slate-100/50 font-medium'
                )"
            >
                <component :is="item.icon" :class="cn('w-5 h-5 mr-4 transition-colors', isItemActive(item) ? 'text-blue-700' : 'text-slate-400 group-hover:text-black')" />
                <span class="flex-1 text-sm text-left">{{ item.label }}</span>
                <ChevronDown v-if="item.children && expandedItems.includes(item.id)" class="w-4 h-4 text-slate-400" />
                <ChevronRight v-else-if="item.children" class="w-4 h-4 text-slate-400" />
            </button>

            <div v-if="item.children && expandedItems.includes(item.id)" class="pl-12 pr-4 py-2 space-y-1">
                <button
                    v-for="child in item.children"
                    :key="child.id"
                    @click="handleNavigate(child.path)"
                    :class="cn(
                        'w-full text-left py-2 text-sm transition-colors rounded-xl px-4',
                        isChildActive(child) ? 'text-blue-700 font-semibold bg-blue-50/50' : 'text-slate-500 hover:text-black hover:bg-slate-100/40'
                    )"
                >
                    {{ child.label }}
                </button>
            </div>
        </div>
      </nav>
    </div>

    <!-- 主展示区 -->
    <div class="flex-1 flex flex-col px-4 md:px-8 pt-6 pb-8 transition-all duration-500 w-full">
        <main class="flex-1 bg-transparent rounded-[2rem] relative z-10 w-full mx-auto">
          <router-view></router-view>
        </main>
    </div>
  </div>
</template>
