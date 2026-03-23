package com.liangtouwu.business.config;

import com.liangtouwu.business.interceptor.AiToolAuthInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Spring MVC 配置
 * 
 * 注册 AI Tool 安全拦截器
 */
@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    private final AiToolAuthInterceptor aiToolAuthInterceptor;

    public WebMvcConfig(AiToolAuthInterceptor aiToolAuthInterceptor) {
        this.aiToolAuthInterceptor = aiToolAuthInterceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(aiToolAuthInterceptor)
                .addPathPatterns("/api/ai-tool/**")
                .order(1);
    }
}
