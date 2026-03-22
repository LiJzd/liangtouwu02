package com.liangtouwu.common.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

/**
 * Spring Security 安全配置类
 * =====================================
 * 本类负责定义系统的整体访问安全策略，包括密码加密方式、跨域资源共享 (CORS) 规则、
 * 以及 HTTP 请求的鉴权拦截控制。
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /**
     * 定义密码哈希算法
     * 采用标准的 BCrypt 算法，确保数据库中存储的是不可逆的密码密文。
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    /**
     * 跨域资源共享 (CORS) 全局配置
     * 允许前端 (Vite/Vue, 通常端口为 5173 或 3000) 跨域调用后端 API。
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        // 设置允许的来源域
        configuration.setAllowedOrigins(List.of(
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000"
        ));
        // 设置允许的 HTTP 方法
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"));
        // 允许所有 Header，但显式暴露 Authorization 头部供前端读取 Token
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setExposedHeaders(List.of("Authorization"));
        configuration.setAllowCredentials(true); // 允许携带 Cookie
        configuration.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    /**
     * HTTP 安全过滤链配置
     */
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                // 禁用 CSRF 防护 (前后端分离架构中通常使用 Token 代替 Cookie 验证，可安全禁用)
                .csrf(AbstractHttpConfigurer::disable)
                // 应用上方定义的 CORS 配置
                .cors(Customizer.withDefaults())
                // 定义鉴权规则
                .authorizeHttpRequests(auth -> auth
                        // ⚠️ 警告：当前项目处于开发/演示阶段，已放开所有请求权限 (anyRequest().permitAll())
                        // 在生产环境下，应对业务接口应用 .authenticated() 或具体角色校验。
                        .anyRequest().permitAll()
                )
                // 配置会话管理：完全无状态 (STATELESS)，不使用 HttpSession 存储安全上下文
                .sessionManagement(session -> session
                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS)
                )
                // 禁用 X-Frame-Options 头部限制，允许页面被 iframe 嵌套 (如管理大屏集成)
                .headers(headers -> headers.frameOptions(frameOptions -> frameOptions.disable()));

        return http.build();
    }
}
