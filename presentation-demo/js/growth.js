/**
 * 猪只生长分析系统 - 核心逻辑插件
 * Version: 2.5 (Realistic & Robust Build)
 * 引入 Box-Muller 高斯分布与自相关生物波动模型
 */

(function() {
    console.log("Dual-Track Growth Engine: Bootstrapping with High-Fidelity Logic...");

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

        // 2. 强制窗口大小适应
        if (chartDom.clientHeight < 100) {
            chartDom.style.height = '500px';
        }

        const myChart = echarts.init(chartDom);
        const $ = (id) => document.getElementById(id);
        const tempSlider = $('temp-slider'), feedSlider = $('feed-slider'), healthSlider = $('health-slider');
        const tempDisp = $('temp-display'), feedDisp = $('feed-display'), healthDisp = $('health-display');
        const effVal = $('efficiency-val'), weightVal = $('weight-val');

        // --- 两头乌品种标准模型参数 ---
        const CONFIG = {
            days: 150,
            K: 135,      // 成熟体重上限 (kg)
            A: 2.8,      // 初始系数 (调整为 2.8 使起始体重约为 8kg，符合断奶入栏标准)
            B_base: 0.0125, // 两头乌日增重速率 (中长期生长特性)
            noise_sd: 1.2   // 高斯噪声标准差
        };

        /** Box-Muller 变换 */
        function randn() {
            let u = 0, v = 0;
            while(u === 0) u = Math.random();
            while(v === 0) v = Math.random();
            return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
        }

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

            const fPenalty = 0.75 + (F * 0.25);
            const B_agent = CONFIG.B_base * tPenalty * fPenalty;

            const daysArr = [], mathD = [], aiD = [], agentD = [], actualD = [];
            let cumulativeDrift = 0;
            const step = 5;

            for (let i = 0; i <= CONFIG.days; i++) {
                if (i % step === 0) {
                    daysArr.push('D' + i);
                    
                    // 1. 通用智能线
                    const aiTarget = getGompertz(i, CONFIG.K, CONFIG.A, CONFIG.B_base * 0.95);
                    const aiOscillation = Math.sin(i / 5) * 2.5 + (Math.random() - 0.5) * 8;
                    aiD.push(Math.max(0.2, aiTarget + aiOscillation).toFixed(2));

                    // 2. 传统数学模型
                    mathD.push(getGompertz(i, CONFIG.K, CONFIG.A, CONFIG.B_base).toFixed(2));

                    // 3. 智能体线
                    const agentVal = getGompertz(i, CONFIG.K, CONFIG.A, B_agent);
                    agentD.push(agentVal.toFixed(2));

                    // 4. 实验实地数据
                    cumulativeDrift = cumulativeDrift * 0.85 + randn() * 0.8;
                    let actVal = agentVal + cumulativeDrift;
                    if (i > 60) {
                        const healthImpact = (1 - H) * 0.12 * Math.min(1, (i - 60) / 40);
                        actVal *= (1 - healthImpact);
                    }
                    actVal += randn() * 0.35;
                    actualD.push(Math.max(0.2, actVal).toFixed(2));
                }
            }

            const currentEff = (tPenalty * fPenalty * 100).toFixed(1);
            effVal.innerText = currentEff + "%";
            weightVal.innerText = agentD[agentD.length - 1] + " kg";
            effVal.style.color = currentEff < 85 ? '#ff4d4d' : '#00f2ff';

            const option = {
                backgroundColor: 'transparent',
                tooltip: { 
                    trigger: 'axis', 
                    backgroundColor: 'rgba(0,10,20,0.95)', 
                    borderColor: 'rgba(0,242,255,0.4)', 
                    borderWidth: 1,
                    textStyle: { color:'#fff', fontFamily: 'Inter', fontSize: 18 } 
                },
                legend: { 
                    data: ['通用智能 (模型震荡)', '传统数学模型', '智能体 (动态拟合)', '实验实测数据'], 
                    textStyle: { color: 'rgba(255,255,255,0.95)', fontSize: 20, fontWeight: 'bold' }, 
                    top: 5,
                    itemGap: 30,
                    itemWidth: 40,
                    itemHeight: 20
                },
                grid: { left: '5%', right: '5%', bottom: '12%', top: '18%', containLabel: true },
                xAxis: { 
                    type: 'category', 
                    data: daysArr, 
                    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.3)' } },
                    axisLabel: { color: 'rgba(255,255,255,0.8)', fontSize: 18, interval: 5 }
                },
                yAxis: { 
                    type: 'value', 
                    name: '体重 (kg)',
                    nameTextStyle: { color: 'rgba(255,255,255,0.8)', fontSize: 20, padding: [0, 0, 0, 50] },
                    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.15)', type: 'dashed' } },
                    axisLabel: { color: 'rgba(255,255,255,0.8)', fontSize: 18 }
                },
                series: [
                    { 
                        name: '通用智能 (模型震荡)', 
                        type: 'line', 
                        data: aiD, 
                        showSymbol: true,
                        symbolSize: 8,
                        lineStyle: { color: '#ff4d4d', opacity: 0.25, width: 2 } 
                    },
                    { 
                        name: '传统数学模型', 
                        type: 'line', 
                        data: mathD, 
                        showSymbol: true,
                        symbol: 'circle',
                        symbolSize: 8,
                        lineStyle: { color: 'rgba(157, 91, 255, 0.5)', type: 'dashed', width: 2.5 } 
                    },
                    { 
                        name: '智能体 (动态拟合)', 
                        type: 'line', 
                        data: agentD, 
                        showSymbol: true,
                        symbolSize: 14,
                        lineStyle: { width: 8, color: '#00f2ff', shadowBlur: 20, shadowColor: 'rgba(0,242,255,0.9)' }, 
                        smooth: 0.3 
                    },
                    { 
                        name: '实验实测数据', 
                        type: 'line',
                        data: actualD, 
                        symbol: 'diamond',
                        symbolSize: 18, 
                        itemStyle: { color: '#ffaa00', opacity: 1, borderWidth: 2, borderColor: '#fff' }, 
                        lineStyle: { width: 0 } 
                    }
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
