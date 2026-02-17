export const APP_CONFIG = {
  APP_NAME: 'My Finance',
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || '/api',
  DEFAULT_CURRENCY: 'KRW',
} as const;
