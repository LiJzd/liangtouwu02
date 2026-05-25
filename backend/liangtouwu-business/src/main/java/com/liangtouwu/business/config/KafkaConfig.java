package com.liangtouwu.business.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * Kafka 基础与 Topic 初始化配置类
 */
// @Configuration
public class KafkaConfig {

    @Value("${ai.kafka.tasks-topic:pig-farm-tasks}")
    private String tasksTopic;

    @Value("${ai.kafka.results-topic:pig-farm-results}")
    private String resultsTopic;

    @Bean
    public NewTopic tasksTopic() {
        return TopicBuilder.name(tasksTopic)
                .partitions(3)
                .replicas(1)
                .build();
    }

    @Bean
    public NewTopic resultsTopic() {
        return TopicBuilder.name(resultsTopic)
                .partitions(3)
                .replicas(1)
                .build();
    }
}
