import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './pages/Dashboard.vue'
import Monitor from './pages/Monitor.vue'
import Analysis from './pages/Analysis.vue'
import Alerts from './pages/Alerts.vue'
import GrowthCurve from './pages/GrowthCurve.vue'
import DailyBriefing from './pages/DailyBriefing.vue'
import Layout from './Layout.vue'

const routes = [
    {
        path: '/',
        component: Layout,
        children: [
            {
                path: '',
                redirect: '/dashboard'
            },
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: Dashboard
            },
            {
                path: 'monitor',
                name: 'Monitor',
                component: Monitor
            },
            {
                path: 'analysis',
                name: 'Analysis',
                component: Analysis
            },
            {
                path: 'growth-curve',
                name: 'GrowthCurve',
                component: GrowthCurve
            },
            {
                path: 'daily-briefing',
                name: 'DailyBriefing',
                component: DailyBriefing
            },
            {
                path: 'alerts',
                name: 'Alerts',
                component: Alerts
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
