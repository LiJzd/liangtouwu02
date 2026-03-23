package com.liangtouwu.domain.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;

/**
 * 生猪 (Pig) 领域实体模型
 * =====================================
 * 该类对应数据库中的 `pig` 表，是系统的核心业务对象。
 * 它记录了每一头生猪的物理身份证号、当前健康评分以及实时传感数据。
 * 
 * 架构说明：
 * - 使用 JPA @Entity 标记，与 Hibernate/MyBatis 联通。
 * - 集成 Lombok (@Data, @Builder) 减少样板代码代码。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "pig")
public class Pig {

    /**
     * 猪只唯一识别编号 (主键)
     * 例如：PIG-001，与耳标号对应。
     */
    @Id
    private String id;

    /**
     * 所属用户 ID（租户隔离字段）
     * 用于多租户环境下的数据隔离
     */
    private String userId;

    /**
     * 综合健康/风险评分
     * 范围：0 (健康) - 100 (极度危险)。
     * 该评分通常由 AI 结合历史体温、活动量及 RAG 知识库计算得出。
     */
    private Integer score;

    /**
     * 异常问题简短描述
     * 用于在列表界面快速提醒兽医，如“疑似高热”、“行动迟缓”等。
     */
    private String issue;

    /**
     * 实时/最新体温
     * 单位：摄氏度 (°C)。
     * 来源：物联网测温挂牌或摄像头视觉还原。
     */
    private BigDecimal bodyTemp;

    /**
     * 当前活跃度等级
     * 范围：0 - 100。
     * 反映猪只的运动频率，低活跃度通常是患病的前兆。
     */
    private Integer activityLevel;
}
