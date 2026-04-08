export interface User {
  id: string;
  email: string;
  nickname: string;
  created_at: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  default_currency: string;
  notification_preferences: NotificationPreferences | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferences {
  budget_alert: boolean;
  maturity_alert: boolean;
  market_alert: boolean;
  email_notifications: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  nickname: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface ProfileUpdateRequest {
  name?: string | null;
  default_currency?: string | null;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface AccountDeleteRequest {
  password: string;
}
