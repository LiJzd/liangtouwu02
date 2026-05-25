package com.liangtouwu.business.service.impl;

import com.liangtouwu.business.mapper.DeviceMapper;
import com.liangtouwu.domain.entity.Device;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Map;

@Service
@EnableScheduling
public class DeviceSimulationService {

    @Autowired
    private DeviceMapper deviceMapper;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    // 定时器计数器，用于控制 24 小时折线数据缓慢滑动（每 15 秒滑动一个时间点）
    private int shiftCounter = 0;

    // 环境初始内存值（与预填充数据同步，用于做连续的增量仿真）
    private double currentTemp = 24.2;
    private double currentHumid = 60.5;
    private double currentNh3 = 4.2;
    private double currentCo2 = 410.0;
    
    private double dailyWaterUsage = 42.8; // 模拟今日已消耗水吨数

    private long lastAlertTime = 0; // 上次发送警报的时间戳，防止高频重复警报

    /**
     * 数字孪生环境仿真物理引擎 (每 3 秒执行一次)
     */
    @Scheduled(fixedDelay = 3000)
    public void simulateEnvironment() {
        try {
            List<Device> devices = deviceMapper.findAll();
            if (devices == null || devices.isEmpty()) {
                return;
            }

            Device fan = null;
            Device ac = null;
            Device water = null;

            for (Device d : devices) {
                if ("fan-1".equals(d.getId())) fan = d;
                else if ("temp-1".equals(d.getId())) ac = d;
                else if ("watering-1".equals(d.getId())) water = d;
            }

            // 1. 恒温空调对舍内温度的模拟计算
            if (ac != null && ac.getState() == 1) {
                // 空调开启：舍温向空调设定值（默认24°C）逼近，增量为 0.1°C
                double targetTemp = ac.getValue() != null ? ac.getValue() : 24.0;
                if (currentTemp < targetTemp) {
                    currentTemp = Math.min(currentTemp + 0.1, targetTemp);
                } else if (currentTemp > targetTemp) {
                    currentTemp = Math.max(currentTemp - 0.1, targetTemp);
                }
            } else {
                // 空调关闭：温度受外界猪群产热与日光辐射影响，自然缓慢爬升至 29.5°C 峰值
                if (currentTemp < 29.5) {
                    currentTemp = Math.min(currentTemp + 0.05, 29.5);
                }
            }
            // 叠加微弱生物随机噪波 jitter (±0.02°C)
            currentTemp += (Math.random() * 0.04) - 0.02;

            // 2. 主风扇与舍内湿度、有害气体（NH3/CO2）的模拟计算
            if (fan != null && fan.getState() == 1) {
                // 风扇开启：空气流通良好，气体浓度在高速抽取下回归安全阈值
                currentNh3 = Math.max(currentNh3 - 0.15, 3.8); // 快速降低，稳定在 3.8-4.2 左右
                currentCo2 = Math.max(currentCo2 - 12.0, 400.0); // 稳定在 400 附近
                currentHumid = Math.max(currentHumid - 0.1, 55.0); // 稳定在 55% 湿度
            } else {
                // 风扇关闭：氨气 NH3 (由猪排泄物不断释放) 快速积累攀升
                currentNh3 = Math.min(currentNh3 + 0.18, 25.0); // 氨气每3秒加0.18ppm，最高封顶 25.0
                currentCo2 = Math.min(currentCo2 + 15.0, 1200.0); // CO2 每3秒加15ppm
                currentHumid = Math.min(currentHumid + 0.15, 78.0); // 湿度增加，封顶 78%
            }
            // 叠加微弱气体波动抖动
            currentNh3 += (Math.random() * 0.06) - 0.03;
            currentCo2 += (Math.random() * 6.0) - 3.0;
            currentHumid += (Math.random() * 0.1) - 0.05;

            // 3. 自动水阀供水量计算
            if (water != null && water.getState() == 1) {
                // 供水开启：累计日用水量缓慢稳定增加
                dailyWaterUsage += 0.005; // 每次仿真增加0.005立方米
            }

            // 4. 超标告警生成闭环逻辑 (NH3 > 12.0 ppm 或 温度 > 29.0°C)
            long now = System.currentTimeMillis();
            if ((currentNh3 > 12.0 || currentTemp > 29.0) && (now - lastAlertTime > 45000)) { // 45秒防高频重复报警
                lastAlertTime = now;
                String timeStr = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date());
                
                if (currentNh3 > 12.0) {
                    String alertMsg = String.format("检测到02栋保育舍氨气浓度异常超标，当前浓度已达 %.2f ppm（安全警戒阈值为 12.00 ppm），排风扇当前处于关闭状态，请立即前往开启排风！", currentNh3);
                    System.out.println("[DeviceSimulationService] !!! DANGER ALERT !!! " + alertMsg);
                    jdbcTemplate.update("INSERT INTO alert (pig_id, area, type, risk, timestamp, message) VALUES (?, ?, ?, ?, ?, ?)",
                            "ENV-NH3", "02栋保育舍", "氨气浓度严重超标", "Critical", timeStr, alertMsg);
                } else if (currentTemp > 29.0) {
                    String alertMsg = String.format("检测到02栋保育舍温度严重偏高，当前舍温已达 %.1f °C，超出适宜区间，为防高热应激，请立即开启恒温空调或风扇降温！", currentTemp);
                    System.out.println("[DeviceSimulationService] !!! DANGER ALERT !!! " + alertMsg);
                    jdbcTemplate.update("INSERT INTO alert (pig_id, area, type, risk, timestamp, message) VALUES (?, ?, ?, ?, ?, ?)",
                            "ENV-TEMP", "02栋保育舍", "猪舍环境温度偏高", "High", timeStr, alertMsg);
                }
            }

            // 5. 写入与更新环境数据库
            updateEnvironmentDatabase();

        } catch (Exception e) {
            System.err.println("[DeviceSimulationService] Error in simulation cycle: " + e.getMessage());
        }
    }

    /**
     * 将仿真数据写回 MySQL 数据库中的 environment_trend 表
     */
    private void updateEnvironmentDatabase() {
        shiftCounter++;
        
        // 5.1 获取最新的环境点 ID
        List<Map<String, Object>> list = jdbcTemplate.queryForList("SELECT id FROM environment_trend ORDER BY id DESC LIMIT 1");
        if (list == null || list.isEmpty()) {
            return;
        }
        
        Long latestId = ((Number) list.get(0).get("id")).longValue();
        
        // 保留两位小数
        BigDecimal formattedTemp = BigDecimal.valueOf(currentTemp).setScale(1, RoundingMode.HALF_UP);
        BigDecimal formattedHumid = BigDecimal.valueOf(currentHumid).setScale(1, RoundingMode.HALF_UP);
        BigDecimal formattedNh3 = BigDecimal.valueOf(currentNh3).setScale(2, RoundingMode.HALF_UP);
        BigDecimal formattedCo2 = BigDecimal.valueOf(currentCo2).setScale(1, RoundingMode.HALF_UP);

        if (shiftCounter >= 5) {
            // 每 15 秒 (5次周期) 发生一次滑动演变：删除最老的一个点，在末尾追加入当前时间点，创造真实的“时间轴平移”特效！
            shiftCounter = 0;
            
            // 获取最老的一条记录 ID 并删除
            List<Map<String, Object>> firstList = jdbcTemplate.queryForList("SELECT id FROM environment_trend ORDER BY id ASC LIMIT 1");
            if (!firstList.isEmpty()) {
                Long oldestId = ((Number) firstList.get(0).get("id")).longValue();
                jdbcTemplate.update("DELETE FROM environment_trend WHERE id = ?", oldestId);
            }
            
            // 新增当前时序点
            String currentHourStr = new SimpleDateFormat("HH:mm").format(new Date());
            jdbcTemplate.update("INSERT INTO environment_trend (time, area, temperature, humidity, nh3, co2) VALUES (?, ?, ?, ?, ?, ?)",
                    currentHourStr, "02栋保育舍", formattedTemp, formattedHumid, formattedNh3, formattedCo2);
            
            System.out.println("[DeviceSimulationService] Trend shifted. New point at: " + currentHourStr 
                    + " | Temp: " + formattedTemp + "°C | NH3: " + formattedNh3 + " ppm | CO2: " + formattedCo2 + " ppm");
        } else {
            // 在同一滑动周期内，仅对最新的终点位置进行高频物理更新，防止数据库记录无线堆积
            jdbcTemplate.update("UPDATE environment_trend SET temperature = ?, humidity = ?, nh3 = ?, co2 = ? WHERE id = ?",
                    formattedTemp, formattedHumid, formattedNh3, formattedCo2, latestId);
        }
    }

    public double getCurrentWaterUsage() {
        return dailyWaterUsage;
    }
}
