import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './pages/Dashboard.vue'
import Monitor from './pages/Monitor.vue'
import Alerts from './pages/Alerts.vue'
import GrowthCurve from './pages/GrowthCurve.vue'
import DailyBriefing from './pages/DailyBriefing.vue'
import PigBot from './pages/PigBot.vue'
import RemoteControl from './pages/RemoteControl.vue'
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
                path: 'pig-bot',
                name: 'PigBot',
                component: PigBot
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
            },
            {
                path: 'remote-control',
                name: 'RemoteControl',
                component: RemoteControl
            }
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
