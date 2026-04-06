package com.liangtouwu.domain.entity;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 测试Pig实体的JSON序列化
 */
public class PigJsonTest {

    @Test
    public void testPigJsonSerialization() throws Exception {
        // 通过反射创建测试数据，避免测试编译阶段直接依赖实体类型
        Class<?> pigClass = Class.forName("com.liangtouwu.domain.entity.Pig");
        Object pig = pigClass.getConstructor().newInstance();
        pigClass.getMethod("setId", String.class).invoke(pig, "PIG001");
        pigClass.getMethod("setUserId", String.class).invoke(pig, "user123");
        pigClass.getMethod("setScore", Integer.class).invoke(pig, 30);
        pigClass.getMethod("setIssue", String.class).invoke(pig, "健康");
        pigClass.getMethod("setBodyTemp", BigDecimal.class).invoke(pig, new BigDecimal("38.5"));
        pigClass.getMethod("setActivityLevel", Integer.class).invoke(pig, 80);
        pigClass.getMethod("setBreed", String.class).invoke(pig, "金华两头乌");
        pigClass.getMethod("setArea", String.class).invoke(pig, "猪舍A");
        pigClass.getMethod("setCurrentWeightKg", BigDecimal.class).invoke(pig, new BigDecimal("45.5"));
        pigClass.getMethod("setCurrentMonth", Integer.class).invoke(pig, 4);

        // 序列化为JSON
        ObjectMapper mapper = new ObjectMapper();
        String json = mapper.writeValueAsString(pig);
        
        System.out.println("序列化结果:");
        System.out.println(json);
        
        // 验证字段名
        assertTrue(json.contains("\"pigId\""), "应该包含pigId字段");
        assertTrue(json.contains("\"current_weight_kg\""), "应该包含current_weight_kg字段");
        assertTrue(json.contains("\"current_month\""), "应该包含current_month字段");
        
        // 验证不应该包含原始字段名
        assertFalse(json.contains("\"id\":"), "不应该包含id字段（应该是pigId）");
        assertFalse(json.contains("\"currentWeightKg\""), "不应该包含currentWeightKg字段");
        assertFalse(json.contains("\"currentMonth\""), "不应该包含currentMonth字段");
    }
}
