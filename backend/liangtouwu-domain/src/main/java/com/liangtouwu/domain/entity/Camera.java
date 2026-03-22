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
 * 摄像头实体类
 * <p>
 * 对应数据库中的 `camera` 表，记录猪舍监控设备的信息。
 * </p>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "camera")
public class Camera {

    /**
     * 摄像头 ID (主键)
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    /**
     * 摄像头名称
     * <p>
     * 例如：猪舍A - 北区
     * </p>
     */
    private String name;
    
    /**
     * 状态
     * <p>
     * 'online' (在线) | 'offline' (离线)
     * </p>
     */
    private String status;
    
    /**
     * 物理位置
     * <p>
     * 例如：猪舍A
     * </p>
     */
    private String location;

    /**
     * 视频流地址
     */
    @jakarta.persistence.Transient
    private String streamUrl;
}
