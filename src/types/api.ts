// API 응답 타입 정의
export interface LoginResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    nickname: string;
    created_at: string;
  };
}

export interface SignupResponse {
  message: string;
  user: {
    id: string;
    email: string;
    nickname: string;
    created_at: string;
  };
}

export interface OAuthResponse {
  auth_url: string;
}

export interface ApiError {
  detail: string;
} 