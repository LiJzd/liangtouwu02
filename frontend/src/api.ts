/**
 * 全局 API 业务接口
 * 统一处理 RESTful 请求和 SSE 流式响应
 */

import http from './utils';

// 业务实体接口模型

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
    risk: 'Critical' | 'High' | 'Medium' | 'Low'; // 风险等级
    timestamp: string;
    message?: string; // 报警附带消息
}

// 统一后端响应包装
interface ApiResponse<T> {
    code: number;
    data: T;
    message: string;
}

// 生猪检测报告流事件类型（对接后端 SSE）
export type InspectionStreamEvent =
    | { event: 'status'; data: { message?: string } } // 状态更新
    | { event: 'chunk'; data: { text?: string } }    // 正文片段
    | { event: 'done'; data: { code?: number; message?: string; pig_id?: string; timestamp?: string } }
    | { event: 'error'; data: { code?: number; message?: string; detail?: string; pig_id?: string } };

// 每日简报流事件类型（对接 /inspection/briefing/stream）
export type BriefingStreamEvent =
    | { event: 'status'; data: { message?: string } }
    | { event: 'chunk'; data: { text?: string } }
    | { event: 'done'; data: { code?: number; message?: string; timestamp?: string } }
    | { event: 'error'; data: { code?: number; message?: string; detail?: string } };

// Mock 数据：后端未启动时使用

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
];

export const MOCK_PIGS_LIST = Array.from({ length: 100 }, (_, i) => {
    const idNum = i + 1;
    const padId = idNum.toString().padStart(3, '0');
    return {
        pigId: `PIG${padId}`,
        breed: '两头乌',
        area: `${['一号舍', '二号舍', '三号舍', '四号舍', '五号舍', '六号舍', '七号舍', '八号舍', '隔离区'][i % 9]}-${['A', 'B', 'C', 'D'][i % 4]}区`,
        current_weight_kg: Math.round((30.0 + Math.random() * 70) * 10) / 10,
        current_month: 2 + (i % 8)
    };
});

// API 服务实现

// 环境变量切换：Mock vs 真实后端
const USE_REAL_API = false; // 强制使用 Mock 数据以展示完整列表
// 模拟延迟
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// 生成模拟简报内容
function generateMockBriefingContent(date: string, dayOffset: number): string {
    const healthScores = [92, 88, 95, 90, 87];
    const avgScore = healthScores[dayOffset % 5];
    const totalPigs = 145 + (dayOffset % 10);
    const abnormalCount = Math.floor(Math.random() * 5);
    const feedConsumption = (1250 + Math.random() * 100).toFixed(1);
    const waterConsumption = (4800 + Math.random() * 200).toFixed(1);
    const avgTemp = (38.5 + Math.random() * 0.5).toFixed(1);
    const envTemp = (22 + Math.random() * 3).toFixed(1);
    const humidity = (65 + Math.random() * 10).toFixed(0);
    const ammonia = (8 + Math.random() * 5).toFixed(1);
    
    return `# ${date} 智慧养殖场智能诊断简报

## 📊 整体概况

今日全场运行状态${avgScore >= 90 ? '**优秀**' : avgScore >= 85 ? '**良好**' : '**正常**'}，系统监测到 **${totalPigs}** 头生猪，平均健康评分 **${avgScore}分**。

### 核心指标

- **在栏总数**: ${totalPigs} 头
- **平均健康评分**: ${avgScore}/100
- **异常个体**: ${abnormalCount} 头
- **平均体温**: ${avgTemp}°C
- **日采食量**: ${feedConsumption} kg
- **日饮水量**: ${waterConsumption} L

## 🏥 健康状况分析

### 体温监测
全场平均体温 **${avgTemp}°C**，处于正常范围（38.0-39.5°C）。${abnormalCount > 0 ? `发现 ${abnormalCount} 头猪只体温略有波动，已标记重点观察。` : '所有猪只体温正常。'}

### 活跃度评估
- 高活跃度: ${Math.floor(totalPigs * 0.7)} 头 (${(70 + Math.random() * 10).toFixed(1)}%)
- 中等活跃度: ${Math.floor(totalPigs * 0.25)} 头 (${(25 + Math.random() * 5).toFixed(1)}%)
- 低活跃度: ${Math.floor(totalPigs * 0.05)} 头 (${(5 + Math.random() * 3).toFixed(1)}%)

${abnormalCount > 0 ? `> **重点关注**: 猪舍B区的异常个体 PIG-B01、猪舍A区的异常个体 PIG-A03 等个体活跃度偏低，建议加强观察。` : ''}

## 🌡️ 环境监测

### 温湿度
- **环境温度**: ${envTemp}°C (适宜范围: 18-24°C)
- **相对湿度**: ${humidity}% (适宜范围: 60-75%)

### 空气质量
- **氨气浓度**: ${ammonia} ppm (警戒值: 15 ppm)
- **二氧化碳**: 正常
- **硫化氢**: 正常

${parseFloat(ammonia) > 12 ? `> **环境提醒**: 氨气浓度略高，建议加强通风。` : ''}

## 🍽️ 饲养管理

### 采食情况
- **日总采食量**: ${feedConsumption} kg
- **人均采食量**: ${(parseFloat(feedConsumption) / totalPigs).toFixed(2)} kg/头
- **采食率**: ${(85 + Math.random() * 10).toFixed(1)}%

### 饮水情况
- **日总饮水量**: ${waterConsumption} L
- **人均饮水量**: ${(parseFloat(waterConsumption) / totalPigs).toFixed(2)} L/头

## 📈 生长趋势

根据AI模型分析，当前批次生猪生长曲线符合预期，预计：
- **平均日增重**: ${(0.6 + Math.random() * 0.2).toFixed(2)} kg
- **预计出栏时间**: ${120 + Math.floor(Math.random() * 20)} 天后
- **预计出栏体重**: ${(95 + Math.random() * 10).toFixed(1)} kg

## ⚠️ 异常预警

${abnormalCount > 0 ? `
今日系统检测到 **${abnormalCount}** 个异常事件：

1. **体温异常** - 猪舍B区 PIG-B01，体温39.8°C，已通知兽医
2. **活跃度低** - 猪舍A区 PIG-A03，活跃度指数32，建议观察
${abnormalCount > 2 ? '3. **采食减少** - 猪舍C区部分猪只采食量下降15%' : ''}

> 所有异常已自动记录并触发语音播报，相关人员已收到通知。
` : `
**无异常事件** - 今日全场运行平稳，未检测到需要人工干预的异常情况。
`}

## 💡 AI 建议

基于今日数据分析，系统提出以下建议：

1. **环境优化**: ${parseFloat(ammonia) > 10 ? '加强猪舍通风，降低氨气浓度' : '保持当前通风频率'}
2. **饲养调整**: ${parseFloat(feedConsumption) / totalPigs < 8 ? '适当增加饲料供应' : '维持当前饲喂方案'}
3. **健康监测**: ${abnormalCount > 0 ? '重点关注标记个体，必要时进行兽医检查' : '继续常规健康巡检'}
4. **预防措施**: 定期消毒，保持环境卫生

---

*本简报由智慧养殖系统自动生成 | 数据采集时间: ${date} 23:59*
*AI 分析引擎版本: v2.1.0 | 置信度: ${(92 + Math.random() * 5).toFixed(1)}%*`;
}

const mockResponse = <T>(data: T): ApiResponse<T> => ({
    code: 200,
    data,
    message: 'Success'
});

const getMockPig = (pigId: string) =>
    MOCK_PIGS_LIST.find((pig) => pig.pigId === pigId) || {
        pigId,
        breed: '待定品种',
        area: '猪舍A',
        current_weight_kg: 45,
        current_month: 4
    };

// 模拟lifecycle历史数据（每月的喂食/饮水/体重记录）
const buildMockLifecycle = (pigId: string) => {
    const pig = getMockPig(pigId);
    const currentMonth = pig.current_month;
    const currentWeight = pig.current_weight_kg;
    // 用固定种子生成稳定的模拟数据
    const seed = pigId.charCodeAt(pigId.length - 1);

    // 计算一个接近 currentWeight 但略低的增重率，确保交汇处有约 4.5kg 的差距（符合用户 4-5kg 的要求）
    const targetLastWeight = currentWeight - 4.5;
    const totalGainNeeded = targetLastWeight - 15;
    const adjustedGain = currentMonth > 1 ? totalGainNeeded / (currentMonth - 1) : 9.0;

    return Array.from({ length: currentMonth }, (_, i) => {
        const month = i + 1;
        // 体重从出生约15kg开始，使用动态计算的增重率
        const weight = Math.round((15 + i * adjustedGain + (seed % 3)) * 10) / 10;
        return {
            month,
            weight_kg: weight,
            feed_count: 44 + (month % 5) + (seed % 4),
            feed_duration_mins: 270 + month * 8 + (seed % 15),
            water_count: 76 + (month % 4) + (seed % 3),
            water_duration_mins: 148 + month * 5 + (seed % 10),
        };
    });
};

const buildMockGrowthCurve = (pigId: string) => {
    const pig = getMockPig(pigId);
    const currentMonth = pig.current_month;
    const currentWeight = pig.current_weight_kg;

    // 标准生长模型 Gompertz 参数：L≈120kg, k=0.28, 拐点 t0≈5.5月
    const gompertz = (m: number) => 120 * Math.exp(-Math.exp(-0.28 * (m - 5.5)));

    // 以实测体重为锚点平移曲线
    const offset = currentWeight - gompertz(currentMonth);
    const endMonth = Math.max(currentMonth + 5, 9);

    return Array.from({ length: endMonth - currentMonth + 1 }, (_, index) => {
        const month = currentMonth + index;
        const adjWeight = Math.round((gompertz(month) + offset) * 10) / 10;
        const gain = index > 0 ? gompertz(month) - gompertz(month - 1) : 0;
        const status = index === 0 ? '当前'
            : gain > 12 ? '快速增重'
            : gain > 8  ? '平稳生长'
            : gain > 5  ? '增速趋缓'
            : month === endMonth ? '建议出栏' : '趋近出栏';

        return {
            month,
            weight: adjWeight,
            status
        };
    });
};


const buildMockPigInspectionReport = (pigId: string) => {
    const pig = getMockPig(pigId);
    const curveData = buildMockGrowthCurve(pigId);
    const lifecycle = buildMockLifecycle(pigId);
    const lastPoint = curveData[curveData.length - 1];
    const gain = (lastPoint.weight - pig.current_weight_kg).toFixed(1);

    // 计算采食/饮水均值用于AI建议
    const avgFeedCount = lifecycle.length > 0
        ? Math.round(lifecycle.reduce((s, d) => s + d.feed_count, 0) / lifecycle.length)
        : 0;
    const avgWaterDuration = lifecycle.length > 0
        ? Math.round(lifecycle.reduce((s, d) => s + d.water_duration_mins, 0) / lifecycle.length)
        : 0;

    // 历史实测数据表格（3列）
    const historicalTable = [
        '### 历史实测数据 (Historical)',
        '',
        '| 月份 | 实测体重(kg) | 状态 |',
        '| --- | --- | --- |',
        ...lifecycle.map(d =>
            `| ${d.month} | ${d.weight_kg} | 已记录 |`
        )
    ].join('\n');

    // 预测曲线表格（3列）
    const predictionTable = [
        '### 预测生长曲线数据 (Monthly)',
        '',
        '| 月份 (Month) | 拟合/预测体重 (kg) | 状态 |',
        '| --- | --- | --- |',
        ...curveData.map((point) => `| ${point.month} | ${point.weight.toFixed(1)} | ${point.status} |`)
    ].join('\n');

    return {
        code: 200,
        message: '模拟结果生成',
        pig_id: pigId,
        report: `# ${pigId} 智能生长分析报告

## 基本信息

- **猪只ID**：\`${pigId}\`
- **品种**：${pig.breed}
- **所在区域**：${pig.area}
- **当前月龄**：${pig.current_month} 月
- **当前体重**：${pig.current_weight_kg.toFixed(1)} kg

## 生长趋势概览

- **预测净增重**：${gain} kg
- **预测结束月龄**：${lastPoint.month} 月
- **目标状态**：${lastPoint.status}

${historicalTable}

${predictionTable}

## AI 建议

1. 保持稳定的管理节奏，避免在快速增重阶段频繁环境变动。
2. 每周复核一次体重，与曲线偏差超过 5kg 时重新评估饲喂方案。
3. 持续关注生猪精神状态，确保猪舍环境舒适。

*报告生成时间：${new Date().toLocaleString('zh-CN')}*`,
        timestamp: new Date().toISOString()
    };
};


export const apiService = {
    // 登录接口
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

    // 获取仪表盘统计数据
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
        // 同步后端的过滤规则：过滤所有以“模拟告警”开头的记录
        let filtered = [...MOCK_ALERTS].filter(a => !a.message?.startsWith('模拟告警'));

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

    /** 预警中心：删除预警记录 */
    deleteAlert: async (id: number | string) => {
        if (USE_REAL_API) {
            const res = await http.delete(`/alerts/${id}`);
            return res.data;
        }

        await delay(400);
        const index = MOCK_ALERTS.findIndex(a => String(a.id) === String(id));
        if (index !== -1) {
            MOCK_ALERTS.splice(index, 1);
        }
        return mockResponse(null);
    },

    /** 预警中心：批量删除预警记录 */
    deleteAlertsBatch: async (ids: (number | string)[]) => {
        if (USE_REAL_API) {
            const res = await http.delete('/alerts/batch', { data: ids });
            return res.data;
        }

        await delay(600);
        ids.forEach(id => {
            const index = MOCK_ALERTS.findIndex(a => String(a.id) === String(id));
            if (index !== -1) MOCK_ALERTS.splice(index, 1);
        });
        return mockResponse(null);
    },

    /** 预警中心：清空所有预警记录 */
    clearAllAlerts: async () => {
        if (USE_REAL_API) {
            const res = await http.delete('/alerts/all');
            return res.data;
        }

        await delay(800);
        MOCK_ALERTS.length = 0;
        return mockResponse(null);
    },

    // 获取所有生猪列表
    getPigsList: async () => {
        if (USE_REAL_API) {
            try {
                const res = await http.get('/pigs/list');
                // 处理ApiResponse包装的数据结构
                if (res.data && res.data.data) {
                    return res.data;
                }
                return res.data || mockResponse(MOCK_PIGS_LIST);
            } catch (e) {
                console.warn('[getPigsList] Java API 不可用，降级到 Mock 数据:', e);
                await delay(300);
                return mockResponse(MOCK_PIGS_LIST);
            }
        }
        await delay(500);
        return mockResponse(MOCK_PIGS_LIST);
    },

    /** 获取历史简报列表 */
    getBriefingHistory: async (limit: number = 10) => {
        const buildMockList = () => {
            const mockBriefings = [];
            const today = new Date();
            for (let i = 0; i < Math.min(limit, 15); i++) {
                const date = new Date(today);
                date.setDate(date.getDate() - i);
                const dateStr = date.toISOString().split('T')[0];
                mockBriefings.push({
                    id: 200 - i,
                    briefingDate: dateStr,
                    summary: `第${i === 0 ? '今' : i}日简报：全场运行${['平稳', '良好', '正常', '优秀'][i % 4]}，${['无异常', '个别关注', '重点监测', '全面健康'][i % 4]}。`,
                    content: generateMockBriefingContent(dateStr, i)
                });
            }
            return mockBriefings;
        };
        if (USE_REAL_API) {
            try {
                const res = await http.get('/briefing/history', { params: { limit } });
                // 处理ApiResponse包装的数据结构
                if (res.data && res.data.data) {
                    return res.data.data;
                }
                return res.data || buildMockList();
            } catch (e) {
                console.warn('[getBriefingHistory] Java API 不可用，降级到 Mock 数据:', e);
                await delay(300);
                return buildMockList();
            }
        }
        await delay(500);
        return buildMockList();
    },

    /** 获取最新一期简报详情 */
    getLatestBriefing: async () => {
        if (USE_REAL_API) {
            const res = await http.get('/briefing/latest');
            // 处理ApiResponse包装的数据结构
            if (res.data && res.data.data) {
                return res.data.data;
            }
            return res.data || null;
        }
        await delay(500);
        return {
            briefingDate: '2026-03-17',
            content: '# 智能简报 (Mock)\n\n今日全场正常。'
        };
    },

    /** 手动触发简报生成 */
    triggerBriefing: async () => {
        if (USE_REAL_API) {
            const res = await http.post('/briefing/trigger', {}, { timeout: 180000 }); // 增加超时时间到3分钟
            // 处理ApiResponse包装的数据结构
            if (res.data && res.data.data) {
                return res.data.data;
            }
            return res.data || null;
        }
        // 模拟生成简报（延迟2秒模拟AI处理时间）
        await delay(2000);
        const today = new Date().toISOString().split('T')[0];
        return {
            id: Date.now(),
            briefingDate: today,
            summary: '今日简报已生成：全场运行优秀，无异常个体。',
            content: generateMockBriefingContent(today, 0)
        };
    },

    /**
     * 流式生成每日简报（直连 AI-service /inspection/briefing/stream）
     * 绕过 Java 后端代理，直接对接 AI 算法服务，实现打字机效果。
     * 注意：此接口生成的简报不会自动入库，入库由 triggerBriefing 负责。
     */
    streamBriefing: async (onEvent: (event: import('./api').BriefingStreamEvent) => void) => {
        // Mock 流式输出（公共函数）
        const runMockStream = async () => {
            onEvent({ event: 'status', data: { message: '正在激活模拟简报链路...' } });
            await delay(600);
            const today = new Date().toISOString().split('T')[0];
            const mockContent = generateMockBriefingContent(today, 0);
            onEvent({ event: 'status', data: { message: '正在构建简报内容帧...' } });
            const chunkSize = 20;
            for (let i = 0; i < mockContent.length; i += chunkSize) {
                onEvent({ event: 'chunk', data: { text: mockContent.slice(i, i + chunkSize) } });
                await delay(30);
            }
            onEvent({ event: 'done', data: { code: 200, message: '简报生成完成', timestamp: new Date().toISOString() } });
        };

        // Mock 模式下模拟流式输出
        if (!USE_REAL_API) {
            await runMockStream();
            return;
        }

        // 真实模式：直连 AI-service 流式端点，失败时 fallback mock
        try {
            const baseUrl = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1';
            const resp = await fetch(`${baseUrl}/inspection/briefing/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (!resp.ok || !resp.body) throw new Error(`简报流连接失败: ${resp.status}`);

            const reader = resp.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

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
                } catch { /* ignore malformed frames */ }
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                let sep = buffer.indexOf('\n\n');
                while (sep !== -1) {
                    parseBlock(buffer.slice(0, sep));
                    buffer = buffer.slice(sep + 2);
                    sep = buffer.indexOf('\n\n');
                }
            }
        } catch (e) {
            console.warn('[streamBriefing] AI 服务不可用，降级到 Mock 流:', e);
            await runMockStream();
        }
    },

    // 同步生成 AI 报告（耗时较长）
    generatePigInspectionReport: async (pigId: string, traceId?: string) => {

        if (!USE_REAL_API) {
            await delay(1500);
            return buildMockPigInspectionReport(pigId);
        }

        const baseUrl = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1';
        const resp = await fetch(`${baseUrl}/inspection/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pig_id: pigId, trace_id: traceId })
        });
        if (!resp.ok) throw new Error(`同步生成失败: ${resp.status}`);
        const data = await resp.json();
        return data;
    },

    // 流式生成报告（SSE 逐字打字机效果）
    streamPigInspectionReport: async (
        pigId: string,
        onEvent: (event: InspectionStreamEvent) => void,
        traceId?: string
    ) => {
        // Mock 流（公共函数）
        const runMockStream = async () => {
            onEvent({ event: 'status', data: { message: '正在激活模拟认知链路...' } });
            await delay(500);
            const mockReport = buildMockPigInspectionReport(pigId);
            const mockMarkdown = mockReport.report;
            onEvent({ event: 'status', data: { message: '正在构建 Markdown 响应帧...' } });
            const chunkSize = 15;
            for (let i = 0; i < mockMarkdown.length; i += chunkSize) {
                onEvent({ event: 'chunk', data: { text: mockMarkdown.slice(i, i + chunkSize) } });
                await delay(40);
            }
            onEvent({ event: 'done', data: { code: 200, pig_id: pigId, timestamp: mockReport.timestamp } });
        };

        // --- Mock 模式下的流模拟逻辑 ---
        if (!USE_REAL_API) {
            await runMockStream();
            return;
        }

        // --- 真实 API 高级流处理逻辑（失败时 fallback mock）---
        try {
            const baseUrl = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1';
            const resp = await fetch(`${baseUrl}/inspection/generate/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pig_id: pigId, trace_id: traceId })
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
        } catch (e) {
            console.warn('[streamPigInspectionReport] AI 服务不可用，降级到 Mock 流:', e);
            await runMockStream();
        }
    },

    /**
     * AI 多智能体聊天接口（针对多模态升级）
     * 支持发送文本、多张图片以及原生音频流。
     */
    chatWithPigBot: async (
        messages: { role: string; content: any }[],
        imageUrls: string[] = [],
        audioBlob: Blob | null = null,
        metadata: any = {}
    ) => {
        const baseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';
        
        // 如果有音频，使用 FormData 以支持多文件上传
        if (audioBlob) {
            const formData = new FormData();
            formData.append('user_id', 'demo_user');
            formData.append('messages', JSON.stringify(messages));
            formData.append('image_urls', JSON.stringify(imageUrls));
            formData.append('audio', audioBlob, 'voice.webm');
            formData.append('metadata', JSON.stringify(metadata));
            
            const res = await fetch(`${baseUrl}/api/v1/agent/chat/v2`, {
                method: 'POST',
                body: formData,
            });
            
            if (!res.ok) {
                const errBody = await res.text();
                throw new Error(`Agent Chat (Multimodal) Failed: ${res.status} - ${errBody}`);
            }
            return await res.json();
        }

        // 兼容原有的 JSON 请求方式（纯文本或带 URL 图片）
        const res = await fetch(`${baseUrl}/api/v1/agent/chat/v2`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "demo_user",
                messages,
                image_urls: imageUrls,
                metadata: metadata
            })
        });
        
        if (!res.ok) {
            const errBody = await res.text();
            throw new Error(`Agent Chat Failed: ${res.status} - ${errBody}`);
        }
        return await res.json();
    },

    /** 语音转文字接口 */
    transcribeAudio: async (audioBlob: Blob): Promise<{ text: string; code: number; message: string }> => {
        const formData = new FormData();
        formData.append('file', audioBlob, 'voice.webm');

        // AI 后端默认端口是 8000
        const baseUrl = import.meta.env.DEV ? 'http://localhost:8000' : '';
        const res = await fetch(`${baseUrl}/api/v1/bot/asr`, {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const errBody = await res.text();
            throw new Error(`ASR Failed: ${res.status} - ${errBody}`);
        }
        return await res.json();
    },

    /**
     * 连接到智能体追踪实时流 (SSE)
     * 获取 ReAct 过程中的 Thought/Action/Observation 推送。
     */
    streamAgentTrace: async (
        clientId: string,
        onEvent: (event: { type: string; data: any; timestamp: string }) => void
    ) => {
        const baseUrl = import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '/api/v1';
        const url = `${baseUrl}/agent/debug/agent-trace?client_id=${clientId}`;
        
        const eventSource = new EventSource(url);
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onEvent(data);
            } catch (e) {
                console.error("Parse agent trace error:", e);
            }
        };
        
        eventSource.onerror = (err) => {
            console.error("Agent trace stream error:", err);
            eventSource.close();
        };
        
        return () => eventSource.close(); // 返回清理函数
    },

    // 获取生长曲线预测数据点
    getGrowthCurve: async (pigId: string) => {
        if (USE_REAL_API) {
            const res = await http.get(`/pigs/${pigId}/growth-curve`);
            // 处理ApiResponse包装的数据结构
            if (res.data && res.data.data) {
                return res.data;
            }
            return res.data || mockResponse([]);
        }
        
        // Mock模式：按当前猪只数据生成稳定曲线
        await delay(500);
        return mockResponse(buildMockGrowthCurve(pigId));
    }
};
