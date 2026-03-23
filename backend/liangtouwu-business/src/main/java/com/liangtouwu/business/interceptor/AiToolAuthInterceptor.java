package com.liangtouwu.business.interceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * AI Tool 接口安全拦截器
 * 
 * 核心职责：
 * 1. 强制校验 X-User-ID Header（防止 AI 提示词注入越权）
 * 2. 拦截所有 /api/ai-tool/** 路径
 * 3. 缺失 Header 时返回 401 Unauthorized
 */
@Slf4j
@Component
public class AiToolAuthInterceptor implements HandlerInterceptor {

    private static final String USER_ID_HEADER = "X-User-ID";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String userId = request.getHeader(USER_ID_HEADER);
        
        if (userId == null || userId.trim().isEmpty()) {
            log.warn("AI Tool 请求缺少 {} Header: path={}, method={}", 
                USER_ID_HEADER, request.getRequestURI(), request.getMethod());
            
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write(
                "{\"code\":401,\"message\":\"缺少 X-User-ID Header，拒绝访问\"}"
            );
            return false;
        }
        
        // 将 userId 存入 Request Attribute，供 Controller 使用
        request.setAttribute("userId", userId.trim());
        
        log.debug("AI Tool 请求通过校验: userId={}, path={}", userId, request.getRequestURI());
        return true;
    }
}
