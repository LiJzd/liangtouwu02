import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';

// --- Types ---

interface User {
  username: string;
  role: string;
  // Add other user properties here
}

interface AuthState {
  token: string | null;
  user: User | null;
}

interface LoginResponse {
  token: string;
  username: string;
  role: string;
  type: string;
}

// --- Configuration ---

const API_BASE_URL = '/api'; // Adjust as needed
const WHITE_LIST = ['/auth/login', '/auth/register'];

// --- State Management (Simple implementation, can be replaced by Pinia/Vuex) ---

class AuthManager {
  private static instance: AuthManager;
  private state: AuthState = {
    token: localStorage.getItem('auth_token'),
    user: this.parseUserFromStorage(),
  };

  private constructor() {}

  static getInstance(): AuthManager {
    if (!AuthManager.instance) {
      AuthManager.instance = new AuthManager();
    }
    return AuthManager.instance;
  }

  getToken(): string | null {
    return this.state.token;
  }

  setToken(token: string) {
    this.state.token = token;
    localStorage.setItem('auth_token', token);
    this.decodeAndSetUser(token);
  }

  clearAuth() {
    this.state.token = null;
    this.state.user = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
  }

  getUser(): User | null {
    return this.state.user;
  }

  private parseUserFromStorage(): User | null {
    const userStr = localStorage.getItem('user_info');
    return userStr ? JSON.parse(userStr) : null;
  }

  private decodeAndSetUser(token: string) {
    try {
      // Basic JWT decoding (payload is the second part)
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));

      const payload = JSON.parse(jsonPayload);
      const user: User = {
        username: payload.sub, // 'sub' is standard for username/subject
        role: payload.role,
      };
      
      this.state.user = user;
      localStorage.setItem('user_info', JSON.stringify(user));
    } catch (e) {
      console.error('Failed to decode token', e);
      this.clearAuth();
    }
  }
}

export const authManager = AuthManager.getInstance();

// --- Axios Interceptor Setup ---

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor
apiClient.interceptors.request.use(
  (config: any) => { // Use 'any' to avoid strict type issues with InternalAxiosRequestConfig if version mismatch
    const url = config.url || '';
    
    // Check if URL is in whitelist
    if (WHITE_LIST.some(path => url.includes(path))) {
      return config;
    }

    const token = authManager.getToken();
    if (token) {
      // Check for token expiration (optional, if decode logic includes exp check)
      // For now, we rely on backend 401
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      // Handle missing token for non-whitelist routes? 
      // Usually better to let 401 handle it, or redirect here.
      console.warn('No token found for protected route');
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response Interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      
      if (status === 401) {
        // Unauthorized: Clear auth and redirect to login
        authManager.clearAuth();
        console.error('Unauthorized! Redirecting to login...');
        // window.location.href = '/login'; // Uncomment to enable auto-redirect
      } else if (status === 403) {
        console.error('Forbidden! You do not have permission.');
      }
    } else {
      console.error('Network Error or No Response');
    }
    return Promise.reject(error);
  }
);

// --- Auth API Helper ---

export const login = async (username: string, password: string): Promise<void> => {
  try {
    const response = await apiClient.post<any>('/auth/login', { username, password });
    // Assuming backend returns ApiResponse<JwtResponse> structure
    // Adjust based on actual backend response: { code: 200, data: { token: '...', ... }, message: '...' }
    const jwtResponse: LoginResponse = response.data.data; 
    if (jwtResponse && jwtResponse.token) {
      authManager.setToken(jwtResponse.token);
    }
  } catch (error) {
    throw error;
  }
};

export const logout = () => {
  authManager.clearAuth();
  // window.location.href = '/login';
};
