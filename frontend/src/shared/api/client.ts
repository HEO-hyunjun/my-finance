import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// JWT 토큰 자동 첨부
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 동시 refresh 요청 방지용 공유 Promise
let refreshPromise: Promise<string> | null = null;

function clearAuthState() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('auth-storage'); // zustand persist 상태도 제거
}

// 401 응답 시 토큰 갱신
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const isAuthRequest = originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/register');
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthRequest) {
      originalRequest._retry = true;

      try {
        if (!refreshPromise) {
          const refreshToken = localStorage.getItem('refresh_token');
          if (!refreshToken) {
            clearAuthState();
            window.location.href = '/login';
            return Promise.reject(error);
          }

          refreshPromise = axios
            .post(`${API_BASE_URL}/v1/auth/refresh`, { refresh_token: refreshToken })
            .then(({ data }) => {
              localStorage.setItem('access_token', data.access_token);
              return data.access_token as string;
            })
            .finally(() => {
              refreshPromise = null;
            });
        }

        const newToken = await refreshPromise;
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch {
        clearAuthState();
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  },
);
