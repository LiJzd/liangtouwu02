/**
 * 全局 API 业务接口封装模块
 * =====================================
 * 本模块是前端与后端沟通的唯一渠道，负责所有数据请求的标准化处理。
 * 
 * 核心特性：
 * 1. 自动切换：支持基于环境变量的环境自动切换（Mock 数据 vs 真实 API）。
 * 2. 类型安全：利用 TypeScript 接口定义了完整的业务实体模型（生猪、摄像头、预警等）。
 * 3. 混合推理支持：同时支持传统的 RESTful 请求和先进的 SSE (Server-Sent Events) 流式报告获取。
 */

import http from './utils';

// --- 业务实体接口模型定义 ---

export interface Camera {
    id: number;
    name: string;
    status: 'online' | 'offline';
    location: string;
    streamUrl?: string; // AI 感知标注流地址
}

export interface Alert {
    id: number;
    pigId: string;
    area: string;
    type: string;
    risk: 'Critical' | 'High' | 'Medium' | 'Low'; // 风险等级枚举
    timestamp: string;
    message?: string; // 报警附带的消息或大模型诊断分析
}

/** 统一后端 API 响应包装 */
interface ApiResponse<T> {
    code: number;
    data: T;
    message: string;
}

/** 
 * 生猪检测报告流事件类型定义 
 * 对应后端 SSE 推送的不同生命周期阶段
 */
export type InspectionStreamEvent =
    | { event: 'status'; data: { message?: string } } // 状态更新（如：正在运行数值轨...）
    | { event: 'chunk'; data: { text?: string } }    // 正文数据碎片（Markdown 正文）
    | { event: 'done'; data: { code?: number; message?: string; pig_id?: string; timestamp?: string } }
    | { event: 'error'; data: { code?: number; message?: string; detail?: string; pig_id?: string } };

// --- 模拟数据 (Mock Data) 系统 ---
// 当后端未启动时，保证前端界面仍能展示完整效果

export const MOCK_DASHBOARD = {
    stockCount: 1580,
    healthRate: 99.2,
    averageTemp: 38.4,
    alertCount: 7,
};

export const MOCK_CAMERAS: Camera[] = [
    { id: 1, name: '一号猪舍 - 北门', status: 'online', location: 'Section A' },
    { id: 2, name: '一号猪舍 - 南门', status: 'online', location: 'Section A' },
    { id: 3, name: '二号猪舍 - 进食区', status: 'offline', location: 'Section B' },
    { id: 4, name: '三号猪舍 - 饮水区', status: 'online', location: 'Section C' },
];

// 生成 24 小时模拟环境趋势
export const MOCK_ENV_TRENDS = Array.from({ length: 24 }, (_, i) => ({
    time: `${i}:00`,
    temperature: 37 + Math.random() * 2,
    humidity: 50 + Math.random() * 10,
}));

export const MOCK_AREA_STATS = [
    { name: '一号舍', temperature: 38.2, humidity: 60 },
    { name: '二号舍', temperature: 37.8, humidity: 55 },
    { name: '三号舍', temperature: 38.5, humidity: 62 },
    { name: '隔离区', temperature: 39.1, humidity: 58 },
];

export const MOCK_ABNORMAL_PIGS = [
    { id: 'PIG-001', score: 95, issue: '疑似持续高热' },
    { id: 'PIG-023', score: 88, issue: '活跃度显著下降' },
    { id: 'PIG-105', score: 76, issue: '检测到攻击性行为' },
    { id: 'PIG-089', score: 65, issue: '进食频率异常' },
    { id: 'PIG-221', score: 60, issue: '行走步态跛行' },
];

export const MOCK_ALERTS: Alert[] = [
    { id: 1, pigId: 'PIG-001', area: '一号舍', type: '发热预警', risk: 'High', timestamp: '2026-03-12 10:00' },
    { id: 2, pigId: 'PIG-023', area: '二号舍', type: '活跃度低', risk: 'Medium', timestamp: '2026-03-12 09:45' },
    { id: 3, pigId: 'PIG-105', area: '一号舍', type: '异常攻击行为', risk: 'Critical', timestamp: '2026-03-12 09:30' },
    // ... 更多预警条目略
];

export const MOCK_PIGS_LIST = [
    { pigId: 'PIG001', breed: '杜洛克', area: '一号舍', current_weight_kg: 45.0, current_month: 3 },
    { pigId: 'PIG002', breed: '陆川猪', area: '一号舍', current_weight_kg: 52.3, current_month: 4 },
    { pigId: 'PIG004', breed: '两头乌', area: '三号舍', current_weight_kg: 40.5, current_month: 3 },
];

// --- API 服务实现 ---

// 控制开关：读取 .env 环境变量中的 VITE_USE_REAL_API 决定是否请求真实后端
const USE_REAL_API = import.meta.env.VITE_USE_REAL_API === 'true';
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const mockResponse = <T>(data: T): ApiResponse<T> => ({
    code: 200,
    data,
    message: 'Success'
});

export const apiService = {
    /** 身份验证：登录接口 */
    login: async (username: string, password: string): Promise<ApiResponse<any>> => {
        if (USE_REAL_API) {
            const res = await http.post('/auth/login', { username, password });
            return res.data;
        }

        await delay(800);
        if (username === 'admin' && password === 'admin') {
            return mockResponse({
                token: 'mock-jwt-token-xyz-123',
                user: { id: 9527, name: '项目管理员', role: 'admin' }
            });
        }
        return { code: 401, data: null, message: '用户名或密码无效' };
    },

    /** 指标数据：获取仪表盘统计 */
    getDashboardStats: async () => {
        if (USE_REAL_API) {
            const res = await http.get('/dashboard/stats');
            return res.data;
        }
        await delay(500);
        return mockResponse(MOCK_DASHBOARD);
    },

    /** 设备管理：获取所有摄像头及流地址 */
    getCameras: async () => {
        if (USE_REAL_API) {
            const res = await http.get('/cameras');
            return res.data.data || res.data; // 返回实际的摄像头数组
        }
        await delay(600);
        return MOCK_CAMERAS;
    },

    /** 环境监控：获取温湿度趋势 */
    getEnvironmentTrends: async () => {
        if (USE_REAL_API) {
            const res = await http.get('/environment/trends');
            return res.data;
        }
        await delay(800);
        return mockResponse(MOCK_ENV_TRENDS);
    },

    /** 环境统计：按区域汇总 */
    getAreaStats: async () => {
        if (USE_REAL_API) {
            const res = await http.get('/area/stats');
            return res.data;
        }
        await delay(600);
        return mockResponse(MOCK_AREA_STATS);
    },

    /** 智能筛查：获取生长异常猪只 */
    getAbnormalPigs: async () => {
        if (USE_REAL_API) {
            const res = await http.get('/pigs/abnormal');
            return res.data;
        }
        await delay(700);
        return mockResponse(MOCK_ABNORMAL_PIGS);
    },

    /** 预警中心：获取预警历史及组合搜索 */
    getAlerts: async (filters: { search?: string; risk?: string; area?: string } = {}) => {
        if (USE_REAL_API) {
            const res = await http.get('/alerts', { params: filters });
            return res.data;
        }

        await delay(500);
        let filtered = [...MOCK_ALERTS];

        // 模拟后端的搜索与过滤逻辑
        if (filters.search) {
            const q = filters.search.toLowerCase();
            filtered = filtered.filter(a => a.pigId.toLowerCase().includes(q) || a.type.toLowerCase().includes(q));
        }

        if (filters.risk && filters.risk !== '全部') {
            filtered = filtered.filter(a => a.risk === filters.risk);
        }

        if (filters.area && filters.area !== '全部') {
            filtered = filtered.filter(a => a.area === filters.area);
        }

        return mockResponse(filtered);
    },

    /** 辅助：获取所有在册生猪列表 (用于选择生成报告) */
    getPigsList: async () => {
        await delay(500);
        return mockResponse(MOCK_PIGS_LIST);
    },

    /** 获取历史简报列表 */
    getBriefingHistory: async (limit: number = 10) => {
        if (USE_REAL_API) {
            const res = await http.get('/briefing/history', { params: { limit } });
            return res.data.data; // 返回实际的数组，而不是整个响应
        }
        await delay(500);
        return [
            { id: 101, briefingDate: '2026-03-17', summary: '今日全场平稳，PIG001 进食略减。' },
            { id: 100, briefingDate: '2026-03-16', summary: '全场活跃度极佳，无异常个体。' }
        ];
    },

    /** 获取最新一期简报详情 */
    getLatestBriefing: async () => {
        if (USE_REAL_API) {
            const res = await http.get('/briefing/latest');
            return res.data.data; // 返回实际的简报对象
        }
        await delay(500);
        return {
            briefingDate: '2026-03-17',
            content: '# 智能简报 (Mock)\n\n今日全场正常。'
        };
    },

    /** 手动触发简报生成 */
    triggerBriefing: async () => {
        const res = await http.post('/briefing/trigger');
        return res.data.data; // 返回实际的简报对象，而不是整个响应
    },

    /** 
     * AI 研判：同步生成报告接口 
     * 适用于报告长度固定且对即时性要求不高的场景。
     */
    generatePigInspectionReport: async (pigId: string) => {
        if (!USE_REAL_API) {
            await delay(800);
            return {
                code: 200,
                message: '模拟结果生成',
                pig_id: pigId,
                report: `# ${pigId} 智能分析报告 (演示模式)\n\n请在开发配置中开启真实 API 以获取 AI 推理结果。`,
                timestamp: new Date().toISOString()
            };
        }

        const res = await http.post(
            '/inspection/generate',
            { pig_id: pigId },
            { timeout: 180000 } // AI 分析较慢，此处将超时时间延长至 3 分钟
        );
        return res.data;
    },

    /** 
     * 核心业务：流式生成报告 (SSE 中转)
     * 利用浏览器 fetch API 原生读取响应体流，实现类似 ChatGPT 的逐字符打字机效果。
     * 
     * @param onEvent 事件回调，用于将接收到的流碎片实时渲染到 UI 组件中。
     */
    streamPigInspectionReport: async (
        pigId: string,
        onEvent: (event: InspectionStreamEvent) => void
    ) => {
        // --- Mock 模式下的流模拟逻辑 ---
        if (!USE_REAL_API) {
            onEvent({ event: 'status', data: { message: '正在激活模拟认知链路...' } });
            await delay(500);
            const mockMarkdown = `# ${pigId} 智能研判结果\n\n报告正在以逐流模式进行模拟输出...`;
            onEvent({ event: 'status', data: { message: '正在构建 Markdown 响应帧...' } });

            const chunkSize = 15;
            for (let i = 0; i < mockMarkdown.length; i += chunkSize) {
                onEvent({ event: 'chunk', data: { text: mockMarkdown.slice(i, i + chunkSize) } });
                await delay(40);
            }

            onEvent({ event: 'done', data: { code: 200, pig_id: pigId, timestamp: new Date().toISOString() } });
            return;
        }

        // --- 真实 API 高级流处理逻辑 ---
        const baseUrl = import.meta.env.DEV ? 'http://localhost:8080/api' : '/api';
        const resp = await fetch(`${baseUrl}/inspection/generate/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pig_id: pigId })
        });

        if (!resp.ok || !resp.body) throw new Error(`流式链接建立失败: ${resp.status}`);

        const reader = resp.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        /** 帧解析函数：识别 SSE 协议中的 event: 和 data: 片段 */
        const parseBlock = (block: string) => {
            const lines = block.split('\n');
            let eventName = 'message';
            const dataParts: string[] = [];

            for (const line of lines) {
                if (line.startsWith('event:')) eventName = line.slice(6).trim();
                if (line.startsWith('data:')) dataParts.push(line.slice(5).trim());
            }

            if (!dataParts.length) return;

            try {
                const data = JSON.parse(dataParts.join('\n'));
                onEvent({ event: eventName as any, data });
            } catch (e) {
                console.error("Malformed SSE frame:", e);
            }
        };

        // 循环读取数据流块
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            // SSE 协议规定双换行符为帧分隔符
            let sep = buffer.indexOf('\n\n');
            while (sep !== -1) {
                parseBlock(buffer.slice(0, sep));
                buffer = buffer.slice(sep + 2);
                sep = buffer.indexOf('\n\n');
            }
        }
    },

    /**
     * AI 多智能体聊天接口（对接 Python AI 端点的 V2 接口）
     * 实际调用 8000 端口，用于多模态交互
     */
    chatWithPigBot: async (
        messages: { role: string; content: any }[],
        imageUrls: string[] = []
    ) => {
        // AI 后端默认端口是 8000，直接调用完整路径
        const baseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';
        const res = await fetch(`${baseUrl}/api/v1/agent/chat/v2`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "demo_user",
                messages,
                image_urls: imageUrls,
                metadata: {}
            })
        });
        
        if (!res.ok) {
            const errBody = await res.text();
            throw new Error(`Agent Chat Failed: ${res.status} - ${errBody}`);
        }
        return await res.json();
    }
};
