package com.liangtouwu.app;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@ComponentScan(basePackages = {"com.liangtouwu.app", "com.liangtouwu.business", "com.liangtouwu.common", "com.liangtouwu.domain"})
@MapperScan("com.liangtouwu.business.mapper")
public class LiangtouwuApplication {
    public static void main(String[] args) {
        SpringApplication.run(LiangtouwuApplication.class, args);
    }
}
