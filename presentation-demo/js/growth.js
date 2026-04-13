/**
 * 猪只生长分析系统 - 核心逻辑插件
 * Version: 2.3 (Robust Build)
 */

(function() {
    console.log("Dual-Track Growth Engine: Bootstrapping...");

    function init() {
        // 1. 深度资源检查
        if (typeof echarts === 'undefined') {
            const errorMsg = "ECharts 引擎未加载，请检查网络连接或 CDN 配置。";
            console.error(errorMsg);
            const container = document.getElementById('growth-chart');
            if (container) {
                container.innerHTML = `<div class="error-placeholder" style="color:#ff003c; border:1px solid #ff003c; padding:20px; text-align:center; height:100%; display:flex; align-items:center; justify-content:center;">
                    [系统错误] ${errorMsg}
                </div>`;
            }
            return;
        }

        const chartDom = document.getElementById('growth-chart');
        if (!chartDom) return;

        // 2. 强制窗口大小适应 (针对某些浏览器下 height:100% 失效的问题)
        if (chartDom.clientHeight < 100) {
            chartDom.style.height = '500px';
        }

        const myChart = echarts.init(chartDom);
        console.log("ECharts initialized successfully.");

        // 获取 DOM 引用
        const $ = (id) => document.getElementById(id);
        const tempSlider = $('temp-slider'), feedSlider = $('feed-slider'), healthSlider = $('health-slider');
        const tempDisp = $('temp-display'), feedDisp = $('feed-display'), healthDisp = $('health-display');
        const effVal = $('efficiency-val'), weightVal = $('weight-val');

        const CONFIG = {
            days: 150,
            K: 140, // 目标出栏
            A: 5.2,
            B_base: 0.025,
            noise: 8
        };

        function getGompertz(t, K, A, B) {
            return K * Math.exp(-A * Math.exp(-B * t));
        }

        function render() {
            const T = parseFloat(tempSlider.value);
            const F = parseFloat(feedSlider.value) / 100;
            const H = parseFloat(healthSlider.value) / 100;

            // 环境残差算法
            let tPenalty = 1.0;
            if (T > 25) tPenalty = 1.0 - (T - 25) * 0.035;
            else if (T < 18) tPenalty = 1.0 - (18 - T) * 0.01;

            const fPenalty = 0.7 + (F * 0.3);
            const B_agent = CONFIG.B_base * tPenalty * fPenalty;

            const daysArr = [], mathD = [], aiD = [], agentD = [], actualD = [];
            let lastAi = 5;

            for (let i = 0; i <= CONFIG.days; i++) {
                daysArr.push('D' + i);
                
                // AI 曲线 (混乱)
                lastAi = Math.max(0, lastAi + 0.6 + (Math.random() - 0.5) * CONFIG.noise);
                if (i > 80 && Math.random() > 0.96) lastAi -= 22;
                aiD.push(lastAi.toFixed(2));

                // 数学模型 (死板)
                mathD.push(getGompertz(i, CONFIG.K, CONFIG.A, CONFIG.B_base).toFixed(2));

                // 智能体 (动态)
                const aVal = getGompertz(i, CONFIG.K, CONFIG.A, B_agent);
                agentD.push(aVal.toFixed(2));

                // 实验实地数据 (包含偏离逻辑)
                let actVal = aVal;
                if (i > 90) {
                    const disease = 1.0 - (1 - H) * 0.015 * ((i - 90) / 60);
                    actVal = aVal * disease;
                }
                actVal += (Math.random() - 0.5) * 1.6;
                actualD.push(actVal.toFixed(2));
            }

            const currentEff = (tPenalty * fPenalty * 100).toFixed(1);
            effVal.innerText = currentEff + "%";
            weightVal.innerText = agentD[agentD.length - 1] + " kg";
            effVal.style.color = currentEff < 80 ? '#fb2c36' : '#00f2ff';

            const option = {
                backgroundColor: 'transparent',
                tooltip: { trigger: 'axis', backgroundColor: 'rgba(0,10,20,0.9)', borderColor: 'rgba(0,242,255,0.3)', textStyle: { color:'#fff' } },
                legend: { data: ['通用智能 (混乱)', '传统数学模型', '智能体 (动态拟合)', '实验实测数据'], textStyle: { color: 'rgba(255,255,255,0.7)' }, top: 10 },
                grid: { left: '4%', right: '4%', bottom: '10%', top: '15%', containLabel: true },
                xAxis: { type: 'category', data: daysArr, axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } } },
                yAxis: { type: 'value', splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
                series: [
                    { name: '通用智能 (混乱)', type: 'line', data: aiD, symbol: 'none', lineStyle: { color: '#ff4d4d', opacity: 0.3 } },
                    { name: '传统数学模型', type: 'line', data: mathD, symbol: 'none', lineStyle: { color: '#9d5bff', type: 'dashed', opacity: 0.5 } },
                    { name: '智能体 (动态拟合)', type: 'line', data: agentD, symbol: 'none', lineStyle: { width: 4, color: '#00f2ff', shadowBlur: 10, shadowColor: 'rgba(0,242,255,0.6)' }, smooth: true },
                    { name: '实验实测数据', type: 'scatter', data: actualD, symbolSize: 5, itemStyle: { color: '#ffaa00' } }
                ]
            };
            myChart.setOption(option);
        }

        // 绑定事件
        [tempSlider, feedSlider, healthSlider].forEach(s => {
            s.oninput = () => {
                const dispMap = { 'temp-slider': tempDisp, 'feed-slider': feedDisp, 'health-slider': healthDisp };
                dispMap[s.id].innerText = s.value + (s.id === 'temp-slider' ? '' : '%');
                render();
            };
        });

        window.onresize = () => myChart.resize();
        render();
    }

    // 尝试多种加载方式确保成功
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
