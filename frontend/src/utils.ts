import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

// Tailwind 类合并组件
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Axios 实例封装

// 响应结构定义
interface ApiResponse<T = any> {
  code?: number;
  data: T;
  message: string;
}

interface HttpErrorInfo {
  status?: number;
  message: string;
  data?: unknown;
  isNetworkError: boolean;
}

// 实例化 Axios
const http: AxiosInstance = axios.create({
  baseURL: '/api', // 统一使用相对路径，由 Vite 代理解决开发环境跨域问题
  timeout: 120000, // 增加到 120 秒（2 分钟），因为 AI 生成简报需要时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
http.interceptors.response.use(
  (response: AxiosResponse<ApiResponse | unknown>) => {
    const res = response.data as any;
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code === 200) return response;
      return Promise.reject({
        status: response.status,
        message: res.message || '业务错误',
        data: res,
        isNetworkError: false,
      } satisfies HttpErrorInfo);
    }
    return response;
  },
  (error) => {
    console.error('Axios Error Details:', {
      message: error.message,
      code: error.code,
      config: error.config,
      response: error.response,
      request: error.request
    });
    
    let message = '';
    const status = error.response?.status;

    switch (status) {
      case 400:
        message = '请求参数错误';
        break;
      case 404:
        message = '接口请求地址不存在';
        break;
      case 500:
        message = '系统服务响应异常';
        break;
      default:
        message = status ? `通讯链路异常 [${status}]` : '网络连接失败，请检查网络状态';
    }

    const structured: HttpErrorInfo = {
      status,
      message,
      data: error.response?.data,
      isNetworkError: !status,
    };

    console.error('HTTP Error:', structured);
    return Promise.reject(structured);
  }
);

export default http;
