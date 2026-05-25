package com.liangtouwu.business.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.Statement;

@Component
public class DatabaseInitializer implements CommandLineRunner {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Override
    public void run(String... args) throws Exception {
        System.out.println("====== [Pocket Piggy] Starting Database Initialization Check ======");
        
        try (Connection conn = jdbcTemplate.getDataSource().getConnection()) {
            DatabaseMetaData metaData = conn.getMetaData();
            
            // 1. 检查并创建 sys_device 表
            boolean hasDeviceTable = false;
            try (ResultSet rs = metaData.getTables(null, null, "sys_device", null)) {
                if (rs.next()) {
                    hasDeviceTable = true;
                }
            }
            
            if (!hasDeviceTable) {
                System.out.println("[DatabaseInitializer] sys_device table does not exist. Creating it...");
                jdbcTemplate.execute("CREATE TABLE sys_device (" +
                        "id VARCHAR(50) PRIMARY KEY," +
                        "name VARCHAR(100) NOT NULL," +
                        "type VARCHAR(20) NOT NULL," +
                        "state TINYINT DEFAULT 0 COMMENT '0=OFF, 1=ON'," +
                        "value INT COMMENT 'setting value'," +
                        "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP" +
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;");
                
                System.out.println("[DatabaseInitializer] Initializing standard control devices seed data...");
                jdbcTemplate.execute("INSERT INTO sys_device (id, name, type, state, value) VALUES " +
                        "('fan-1', '01栋主风扇', 'fan', 1, 65), " +
                        "('light-1', '保育舍照明', 'light', 0, 0), " +
                        "('temp-1', '恒温空调系统', 'temp', 1, 24), " +
                        "('watering-1', '自动供水水阀', 'watering', 1, 35);"); // 35 represents 0.35 MPa
                System.out.println("[DatabaseInitializer] sys_device initialized successfully.");
            } else {
                System.out.println("[DatabaseInitializer] sys_device table already exists.");
            }
            
            // 2. 检查并扩容 environment_trend 字段 (nh3, co2)
            boolean hasNh3 = false;
            boolean hasCo2 = false;
            try (ResultSet rs = metaData.getColumns(null, null, "environment_trend", "nh3")) {
                if (rs.next()) {
                    hasNh3 = true;
                }
            }
            try (ResultSet rs = metaData.getColumns(null, null, "environment_trend", "co2")) {
                if (rs.next()) {
                    hasCo2 = true;
                }
            }
            
            if (!hasNh3) {
                System.out.println("[DatabaseInitializer] Adding nh3 column to environment_trend...");
                jdbcTemplate.execute("ALTER TABLE environment_trend ADD COLUMN nh3 DECIMAL(10, 2) DEFAULT 4.20 COMMENT 'NH3 ppm';");
            }
            if (!hasCo2) {
                System.out.println("[DatabaseInitializer] Adding co2 column to environment_trend...");
                jdbcTemplate.execute("ALTER TABLE environment_trend ADD COLUMN co2 DECIMAL(10, 2) DEFAULT 410.0 COMMENT 'CO2 ppm';");
            }
            
            // 3. 为时序走势图预填充 24 小时数据（如果数据过少）
            Integer count = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM environment_trend", Integer.class);
            if (count != null && count < 24) {
                System.out.println("[DatabaseInitializer] Initial trend points count is low (" + count + "). Pre-populating 24 points...");
                jdbcTemplate.execute("DELETE FROM environment_trend"); // 清空重写
                
                String area = "02栋保育舍";
                for (int i = 0; i < 24; i++) {
                    String hourStr = String.format("%02d:00", i);
                    double baseTemp = 24.0 + Math.sin(i * Math.PI / 12) * 1.5;
                    double baseHumid = 60.0 + Math.cos(i * Math.PI / 12) * 5.0;
                    double baseNh3 = 4.2 + Math.random() * 0.8;
                    double baseCo2 = 410.0 + Math.random() * 30.0;
                    
                    jdbcTemplate.update("INSERT INTO environment_trend (time, area, temperature, humidity, nh3, co2) VALUES (?, ?, ?, ?, ?, ?)",
                            hourStr, area, baseTemp, baseHumid, baseNh3, baseCo2);
                }
                System.out.println("[DatabaseInitializer] 24 environment trend points pre-populated successfully.");
            }
            
        } catch (Exception e) {
            System.err.println("[DatabaseInitializer] FAILED to initialize database check: " + e.getMessage());
            e.printStackTrace();
        }
        System.out.println("====== [Pocket Piggy] Database Initialization Check COMPLETED ======");
    }
}
