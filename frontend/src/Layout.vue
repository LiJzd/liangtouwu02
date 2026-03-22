<script setup lang="ts">
/**
 * 全局工作台布局 (Layout) - 比赛简化版
 * =====================================
 * 本组件已移除所有身份识别与账户管理逻辑，专注于纯粹的养殖业务展示。
 */
import { ref, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { 
  Bell, 
  Search, 
  ChevronDown, 
  ChevronRight,
  Warehouse, 
  LayoutDashboard, 
  MonitorPlay, 
  Activity, 
  AlertTriangle, 
  PiggyBank,
  TrendingUp
} from 'lucide-vue-next';
import { cn } from './utils';

const router = useRouter();
const route = useRoute();

const expandedItems = ref<string[]>(['analysis']);

/** 核心业务导航菜单 */
const NAV_ITEMS = [
  { id: 'dashboard', label: '主控看板', subLabel: 'DASHBOARD', icon: LayoutDashboard, path: '/dashboard' },
  { id: 'monitor', label: '实时监控', subLabel: 'MONITOR', icon: MonitorPlay, path: '/monitor' },
  { 
    id: 'analysis', 
    label: '深度分析', 
    subLabel: 'ANALYSIS', 
    icon: Activity,
    path: '/analysis', 
    children: [
      { id: 'analysis', label: '全域横向对比', path: '/analysis' },
      { id: 'analysis-area-a', label: '猪舍 A 区趋势', path: '/analysis?area=猪舍 A 区' }, 
      { id: 'analysis-area-b', label: '猪舍 B 区趋势', path: '/analysis?area=猪舍 B 区' },
      { id: 'analysis-area-c', label: '猪舍 C 区趋势', path: '/analysis?area=猪舍 C 区' },
    ]
  },
  { id: 'growth-curve', label: '生长预测', subLabel: 'GROWTH CURVE', icon: TrendingUp, path: '/growth-curve' },
  { id: 'daily-briefing', label: '每日简报', subLabel: 'DAILY BRIEF', icon: Warehouse, path: '/daily-briefing' },
  { id: 'alerts', label: '风险控制', subLabel: 'ALERTS', icon: AlertTriangle, path: '/alerts' },
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
  <div class="min-h-screen bg-slate-50 flex">
    <!-- 固定侧边栏 -->
    <div class="w-64 h-screen bg-slate-50 border-r border-slate-200 fixed left-0 top-0 flex flex-col z-20">
      <div class="h-16 flex items-center px-6 border-b border-slate-200">
        <PiggyBank class="w-6 h-6 text-blue-600 mr-3" />
        <div>
          <h1 class="text-base font-bold text-slate-900 tracking-wider">两头乌智慧养殖</h1>
          <p class="text-[10px] text-slate-500 font-mono tracking-widest uppercase">Breeding OS V2</p>
        </div>
      </div>
      
      <nav class="flex-1 py-6 space-y-1 overflow-y-auto">
        <div class="px-6 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest font-mono">控制台总览</div>
        <div v-for="item in NAV_ITEMS" :key="item.id">
            <button
                @click="item.children ? toggleExpand(item.id) : handleNavigate(item.path)"
                :class="cn(
                  'w-full flex items-center px-6 py-3 transition-colors group border-l-4',
                  isItemActive(item)
                    ? 'border-blue-600 bg-blue-50 text-blue-700' 
                    : 'border-transparent text-slate-500 hover:bg-slate-100'
                )"
            >
                <component :is="item.icon" :class="cn('w-4 h-4 mr-3', isItemActive(item) ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-500')" />
                <span class="flex-1 text-sm font-medium text-left">{{ item.label }}</span>
                <ChevronDown v-if="item.children && expandedItems.includes(item.id)" class="w-3 h-3 text-slate-400" />
                <ChevronRight v-else-if="item.children" class="w-3 h-3 text-slate-400" />
            </button>

            <div v-if="item.children && expandedItems.includes(item.id)" class="bg-slate-50 border-y border-slate-200">
                <button
                    v-for="child in item.children"
                    :key="child.id"
                    @click="handleNavigate(child.path)"
                    :class="cn(
                        'w-full flex items-center pl-14 pr-6 py-2 text-xs font-medium transition-colors',
                        isChildActive(child) ? 'text-blue-700 bg-blue-50 border-l-2 border-blue-600 ml-[2px]' : 'text-slate-500 hover:text-slate-900'
                    )"
                >
                    <span :class="cn('w-1.5 h-1.5 rounded-none mr-2', isChildActive(child) ? 'bg-blue-600' : 'bg-slate-300')"></span>
                    {{ child.label }}
                </button>
            </div>
        </div>
      </nav>
      
      <div class="p-6 border-t border-slate-200 text-center">
            <p class="text-[10px] text-slate-400 font-mono">NODE-CORE: ONLINE</p>
      </div>
    </div>

    <!-- 主展示区 -->
    <div class="flex-1 flex flex-col ml-64">
        <!-- 顶部工具栏 - 已移除用户识别与账户切换 -->
        <header class="h-16 bg-white border-b border-slate-200 fixed top-0 left-64 right-0 z-50 px-6 flex items-center justify-between shadow-sm">
          <div class="flex items-center">
            <div class="flex items-center text-slate-500 bg-slate-50 px-3 py-2 border border-slate-300 w-80">
              <Search class="w-4 h-4 mr-3 text-slate-400" />
              <input type="text" placeholder="多功能指令检索..." class="bg-transparent border-none focus:outline-none text-sm font-mono text-slate-700 w-full" />
            </div>
          </div>
          
          <div class="flex items-center space-x-6">
            <!-- 场区切换保留，这属于业务范畴 -->
            <div class="relative group">
              <button class="flex items-center space-x-2 px-3 py-2 hover:bg-slate-50 text-slate-700 text-sm font-bold border border-transparent hover:border-slate-200">
                <Warehouse class="w-4 h-4 text-blue-600" />
                <span>金华一号分拣场</span>
                <ChevronDown class="w-3 h-3 text-slate-400" />
              </button>
              <div class="absolute right-0 top-full mt-0 w-56 bg-white border border-slate-200 hidden group-hover:block z-50 shadow-lg">
                <div class="px-4 py-2 text-[10px] font-bold text-slate-400 bg-slate-50 uppercase">监测站点切换</div>
                <button class="w-full text-left px-4 py-3 text-xs font-mono hover:bg-slate-50 border-b border-slate-100 flex justify-between">
                  <span>金华一号场</span><span class="w-2 h-2 bg-blue-600"></span>
                </button>
                <button class="w-full text-left px-4 py-3 text-xs font-mono hover:bg-slate-50 border-b border-slate-100 flex justify-between">
                  <span>义乌二号场</span>
                </button>
                <button class="w-full text-left px-4 py-3 text-xs font-mono hover:bg-slate-50">东阳种猪场</button>
              </div>
            </div>

            <div class="h-8 w-px bg-slate-200"></div>

            <!-- 通知中心 -->
            <button class="relative group p-2 hover:bg-slate-100 border border-transparent" title="系统通知">
              <Bell class="w-5 h-5 text-slate-600" />
              <span class="absolute top-1 right-1 w-2 h-2 bg-red-600 border border-white"></span>
            </button>
            
            <!-- 视觉补偿：保留一个静态标识，而非动态账户系统 -->
            <div class="flex items-center space-x-3 pl-2">
                 <div class="h-8 w-8 bg-slate-100 flex items-center justify-center text-slate-400 border border-slate-200">
                    <PiggyBank class="w-4 h-4" />
                 </div>
                 <div class="text-left hidden md:block">
                  <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Breeding Node</p>
                  <p class="text-[10px] text-slate-500 font-mono">STATUS: MASTER</p>
                </div>
            </div>
          </div>
        </header>

        <main class="flex-1 mt-16 p-6 overflow-auto bg-slate-50">
          <router-view></router-view>
        </main>
    </div>
  </div>
</template>
