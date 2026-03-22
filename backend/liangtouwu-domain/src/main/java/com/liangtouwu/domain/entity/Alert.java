package com.liangtouwu.domain.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 报警信息实体类
 * <p>
 * 对应数据库中的 `alert` 表，记录系统生成的异常报警。
 * </p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "alert")
public class Alert {

    /**
     * 报警 ID (主键)
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * 相关猪只 ID
     */
    private String pigId;

    /**
     * 发生位置
     * <p>
     * 例如：猪舍A
     * </p>
     */
    private String area;

    /**
     * 报警类型
     * <p>
     * 例如：发热、受伤
     * </p>
     */
    private String type;

    /**
     * 风险等级
     * <p>
     * 'Low', 'Medium', 'High', 'Critical'
     * </p>
     */
    private String risk;

    /**
     * 报警时间
     * <p>
     * 字符串格式的时间戳
     * </p>
     */
    private String timestamp;
}
