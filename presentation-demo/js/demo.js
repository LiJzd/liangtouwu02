document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatLeft = document.getElementById('chat-left');
    const chatMiddle = document.getElementById('chat-middle');
    const chatRight = document.getElementById('chat-right');

    const SIMULATOR = {
        'PIG001': {
            normal: "PIG001 目前生长状况非常出色，预估体重大约在 105kg 左右。",
            basic: [
                { type: 'action', tool: 'fetch_realtime_weight', input: '{"id": "PIG001"}' },
                { type: 'observation', content: '{"val": "98.2", "unit": "kg"}' },
                { type: 'final', content: '查询完成。PIG001 实时体重为 98.2kg。' }
            ],
            react: [
                { type: 'thought', title: 'Cognitive (逻辑解析)', content: '检测到目标编号 PIG001。正绕过缓存建立实时链路，从硬件层调取最新生长数据。' },
                { type: 'action', title: 'System [Execute]', tool: 'fetch_realtime_weight', input: '{"id": "PIG001", "bypass_cache": true}' },
                { type: 'observation', title: 'Hardware [Feedback]', content: 'RESULT_OK: {"val": "98.2", "unit": "kg", "ts": 1712992341}' },
                { type: 'final', title: 'Agent [Decision]', content: '✅ **PIG001 查询完成**：\n物理传感器确认实时体重为 **98.2kg**。该数值已同步至本地档案，确认为此时刻的真实物理指标。' }
            ]
        },
        'PIG099': {
            normal: "PIG099 目前状态非常稳定，它正在 5 号猪舍进食。",
            basic: [
                { type: 'action', tool: 'query_registry', input: '{"target": "PIG099"}' },
                { type: 'observation', content: 'HTTP_404: NOT_FOUND' },
                { type: 'error', content: 'TypeError: Cannot read properties of null (reading "location")\n    at Agent.parseResponse (agent.js:142)\n    at process.run (worker.js:89)' }
            ],
            react: [
                { type: 'thought', title: 'Cognitive (一致性核查)', content: '检索 PIG099 标识符。我需要首先在物理资产库中确认其 RegistryID，任何基于文本推算的响应将被标记为潜在幻觉。' },
                { type: 'action', title: 'System [Execute]', tool: 'query_registry', input: '{"target": "PIG099"}' },
                { type: 'observation', title: 'Database [Response]', content: 'HTTP_404: RESOURCE_NOT_FOUND' },
                { type: 'thought', title: 'Analysis (真伪判定)', content: '查询结果为 NULL。确认 PIG099 在当前物理牧场中不具有合法索引。根据诚实性协议，我将截断该幻觉分支，拒绝提供其在 5 号舍的虚假细节。' },
                { type: 'final', title: 'Agent [Decision]', content: '❌ **系统查无此猪**：\nPIG099 在本场档案中不存在。建议重新确认编号。' }
            ]
        },
        'default': {
            normal: "您好！我是两头乌智能助手，有什么可以帮您？",
            basic: [{ type: 'final', content: '您好，请指定猪只编号。' }],
            react: [
                { type: 'thought', title: 'Status (待命)', content: '神经元集群已就绪。正在检测特定猪只 ID 以激活深度推理协议。' },
                { type: 'final', title: 'System [Info]', content: '欢迎使用 ReAct 推理中心。输入特定编号（如 PIG001）即可查看对比结果。' }
            ]
        }
    };

    async function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // --- Hyper-Streaming 打字机逻辑 ---
    async function hyperType(text, element, isFinal = false) {
        element.innerHTML = '';
        // 插入光标
        const cursor = document.createElement('span');
        cursor.className = 'cursor';
        element.appendChild(cursor);

        const contentSpan = document.createElement('span');
        element.insertBefore(contentSpan, cursor);

        const lines = text.split('\n');
        for (let l = 0; l < lines.length; l++) {
            const line = lines[l];
            for (let char of line) {
                contentSpan.innerHTML += char;
                // 模拟“思考节奏”：随机变速
                const speed = 40 + Math.random() * 60; // 调慢打字速度
                await sleep(speed);
                // 自动跟随滚动
                const scrollParent = element.closest('.chat-canvas');
                if (scrollParent) scrollParent.scrollTop = scrollParent.scrollHeight;
            }
            if (l < lines.length - 1) contentSpan.innerHTML += '<br>';
        }

        // 完成后移除或停止光标
        if (!isFinal) {
            cursor.remove();
        }
    }

    function createTimeline(container) {
        if (!container.querySelector('.timeline-track')) {
            const line = document.createElement('div');
            line.className = 'timeline-track';
            container.appendChild(line);
        }
    }

    async function addStep(step, container) {
        const node = document.createElement('div');
        node.className = `react-node`;
        
        node.innerHTML = `
            <div class="node-bullet"></div>
            <div class="node-card">
                <div class="node-header">
                    <span class="node-title">${step.title}</span>
                </div>
                <div class="node-content"></div>
            </div>
        `;
        
        container.appendChild(node);
        const contentBox = node.querySelector('.node-content');

        if (step.type === 'thought' || step.type === 'final') {
            const target = (step.type === 'final') ? document.createElement('div') : contentBox;
            if(step.type === 'final') {
                target.className = 'final-wrap';
                contentBox.appendChild(target);
            }
            // 🚀 这里是思维链的每一个字的产出点
            await hyperType(step.content, target, step.type === 'final');
        } else if (step.type === 'action') {
            contentBox.innerHTML = `<div class="terminal-block">
                <span style="color:#00ff41">> RUN_TOOL:</span> ${step.tool}<br>
                <span style="color:rgba(0,242,255,0.5)">> PARAM_STREAM:</span> ${step.input}
            </div>`;
            await sleep(1500); // 模拟工具调用耗时
        } else if (step.type === 'observation') {
             contentBox.innerHTML = `<div class="terminal-block">
                <span style="color:#ffaa00">> RECV_DATA:</span> ${step.content}
            </div>`;
            await sleep(1200); // 模拟数据回传耗时
        }

        container.closest('.chat-canvas').scrollTop = container.closest('.chat-canvas').scrollHeight;
    }

    async function startDemo() {
        const query = userInput.value.trim().toUpperCase();
        if (!query) return;

        userInput.value = '';
        chatLeft.innerHTML = '';
        chatMiddle.innerHTML = '';
        chatRight.innerHTML = '';

        // 显示用户提问
        const createMsg = (txt, cls) => {
            const div = document.createElement('div');
            div.className = cls;
            div.innerText = txt;
            return div;
        };

        chatLeft.appendChild(createMsg(query, 'message user'));
        chatMiddle.appendChild(createMsg(query, 'message user'));
        chatRight.appendChild(createMsg(query, 'message user'));

        const normalizedQuery = query.replace(/\s+/g, '');
        let key = 'default';
        if (/PIG(ID)?0*99/i.test(normalizedQuery) || normalizedQuery.includes('99')) key = 'PIG099';
        else if (/PIG(ID)?0*01/i.test(normalizedQuery) || normalizedQuery.includes('01')) key = 'PIG001';

        const data = SIMULATOR[key];

        // --- 1. 左侧：通用大模型 (带延迟，模拟慢速) ---
        const botLeft = document.createElement('div');
        botLeft.className = 'message bot';
        chatLeft.appendChild(botLeft);
        setTimeout(() => hyperType(data.normal, botLeft), 4000);

        // --- 2. 中间：基础 Agent (简单流程) ---
        const basicWrapper = document.createElement('div');
        basicWrapper.className = 'message bot';
        chatMiddle.appendChild(basicWrapper);
        
        const runBasic = async () => {
            await sleep(1000);
            for(const step of data.basic) {
                if(step.type === 'action') {
                    basicWrapper.innerHTML += `<div class="terminal-block"><b>> CALL_TOOL:</b> ${step.tool}</div>`;
                } else if(step.type === 'observation') {
                    await sleep(800);
                    basicWrapper.innerHTML += `<div class="terminal-block" style="border-left-color:var(--neon-cyan)"><b>> RETURN:</b> ${step.content}</div>`;
                } else if(step.type === 'error') {
                    await sleep(1000);
                    basicWrapper.innerHTML += `<div class="terminal-error"><b>[CRITICAL_BUG]</b><br>${step.content}</div>`;
                } else if(step.type === 'final') {
                    await sleep(500);
                    const finalDiv = document.createElement('div');
                    finalDiv.style.marginTop = '10px';
                    basicWrapper.appendChild(finalDiv);
                    await hyperType(step.content, finalDiv, true);
                }
                chatMiddle.scrollTop = chatMiddle.scrollHeight;
                await sleep(1000);
            }
        };
        runBasic();

        // --- 3. 右侧：注入 React 模板的智能体 ---
        const reactWrapper = document.createElement('div');
        reactWrapper.className = 'message bot react-chain';
        chatRight.appendChild(reactWrapper);
        createTimeline(reactWrapper);

        const runReact = async () => {
            for (const step of data.react) {
                await sleep(1200 + Math.random() * 300);
                await addStep(step, reactWrapper);
            }
        };
        runReact();
    }

    sendBtn.addEventListener('click', startDemo);
    userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') startDemo(); });
});
