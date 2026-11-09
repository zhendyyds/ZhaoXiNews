/**
 * API配置文件
 * 包含后端 API 基础 URL
 */

// API基础URL配置
export const apiConfig = {
  // 后端API基础URL
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8000',
}

