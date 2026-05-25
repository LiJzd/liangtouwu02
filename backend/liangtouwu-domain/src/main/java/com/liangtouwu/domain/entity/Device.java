package com.liangtouwu.domain.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Date;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "sys_device")
public class Device {

    @Id
    private String id;
    private String name;
    private String type;
    private Integer state; // 0 = OFF, 1 = ON
    private Integer value; // setting value (speed %, AC temp, etc.)
    private Date updatedAt;
}
