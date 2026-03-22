package com.liangtouwu.common.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 统一 API 响应包装类
 * <p>
 * 所有 REST 接口返回的数据都应封装在此类中，以保证前后端交互格式的一致性。
 * </p>
 *
 * @param <T> 响应数据的泛型类型
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {

    /**
     * 响应状态码
     * <p>
     * 200 表示成功，其他值通常表示错误代码
     * </p>
     */
    private int code;

    /**
     * 响应业务数据
     */
    private T data;

    /**
     * 响应消息
     * <p>
     * 成功时通常为 "Success"，失败时包含具体的错误描述
     * </p>
     */
    private String message;

    /**
     * 构建成功响应
     *
     * @param data 业务数据
     * @param <T>  数据类型
     * @return 状态码为 200 的成功响应对象
     */
    public static <T> ApiResponse<T> success(T data) {
        return ApiResponse.<T>builder()
                .code(200)
                .data(data)
                .message("Success")
                .build();
    }

    /**
     * 构建错误响应
     *
     * @param code    错误状态码
     * @param message 错误描述信息
     * @param <T>     数据类型
     * @return 包含错误信息的响应对象
     */
    public static <T> ApiResponse<T> error(int code, String message) {
        return ApiResponse.<T>builder()
                .code(code)
                .message(message)
                .build();
    }
}
