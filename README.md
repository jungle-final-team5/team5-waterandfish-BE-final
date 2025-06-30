# 수어지교 (Team5 Water and Fish)

손끝에서 시작되는 인연 - 수어 학습 및 커뮤니티 플랫폼

## 프로젝트 구조

```
team5-waterandfish-BE/
├── src/
│   ├── api/           # API 라우터
│   ├── core/          # 설정 및 인증
│   ├── db/            # 데이터베이스 연결
│   ├── models/        # Pydantic 모델
│   ├── services/      # 비즈니스 로직
│   └── main.py        # FastAPI 앱 진입점
├── tests/             # 테스트 파일
├── pyproject.toml     # Python 의존성
└── README.md
```

## 백엔드 (FastAPI + MongoDB)

### 설치 및 실행

1. Python 3.9+ 설치
2. Poetry 설치
3. 의존성 설치:
```bash
poetry install
```

4. 환경 변수 설정 (.env 파일):
```env
MONGODB_URL=mongodb://localhost:27017
JWT_SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
KAKAO_CLIENT_ID=your-kakao-client-id
KAKAO_CLIENT_SECRET=your-kakao-client-secret
```

5. 서버 실행:
```bash
poetry run uvicorn src.main:app --reload
```

### API 엔드포인트

- `POST /auth/signin` - 로그인
- `POST /auth/signup` - 회원가입
- `DELETE /auth/delete-account` - 회원 탈퇴 (이메일 검증)
- `GET /auth/google` - Google OAuth 시작
- `GET /auth/kakao` - Kakao OAuth 시작
- `POST /auth/{provider}/callback` - OAuth 콜백 처리

## 프론트엔드 (React + TypeScript)

### 설치 및 실행

1. Node.js 16+ 설치
2. 의존성 설치:
```bash
npm install
```

3. 환경 변수 설정 (.env 파일):
```env
REACT_APP_API_URL=http://localhost:8000
```

4. 개발 서버 실행:
```bash
npm start
```

### 주요 컴포넌트

- `src/pages/Login.tsx` - 로그인 페이지
- `src/pages/Signup.tsx` - 회원가입 페이지
- `src/pages/Home.tsx` - 홈 페이지
- `src/pages/OAuthCallback.tsx` - OAuth 콜백 처리
- `src/components/AxiosInstance.ts` - API 클라이언트

## 기능

- ✅ 사용자 인증 (이메일/비밀번호)
- ✅ 소셜 로그인 (Google, Kakao)
- ✅ JWT 토큰 기반 인증
- ✅ MongoDB 데이터 저장
- ✅ 반응형 UI (Tailwind CSS)
- ✅ TypeScript 타입 안전성

## 기술 스택

### 백엔드
- FastAPI
- MongoDB (Motor)
- PyJWT
- Pydantic v2
- Poetry

### 프론트엔드
- React 18
- TypeScript
- React Router v6
- Axios
- Tailwind CSS
