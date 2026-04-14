# SlideCraft AI - Next.js client

SlideCraft AI의 FastAPI 백엔드를 로컬에서 테스트하기 위한 Next.js 프론트엔드입니다.

이 프레젠테이션 UI는 [Figma](https://www.figma.com/design/eyDAHbNevAlfRz1P2e4C5G/AI-Presentation-Generator-UI)의 **AI Presentation Generator UI**를 기반으로 합니다. 서드파티 크레딧은 [ATTRIBUTIONS.md](./ATTRIBUTIONS.md)를 참고하세요.

## 요구 사항

- Node.js 20 이상
- npm 10 이상
- 같은 워크스페이스에 있는 FastAPI 백엔드 프로젝트

## 실행 전 환경 변수 설정

이 프로젝트는 백엔드 주소를 코드에 하드코딩하지 않고 환경 변수로 관리합니다.

`nextjs-app/.env.local` 파일에 아래 값을 설정하세요.

```env
# 브라우저에서 직접 호출할 FastAPI 주소
NEXT_PUBLIC_BACKEND_BASE_URL=http://127.0.0.1:8000

# 서버사이드 API 라우트에서 사용할 백엔드 주소
# 비워두면 NEXT_PUBLIC_BACKEND_BASE_URL 값을 함께 사용할 수 있습니다.
BACKEND_BASE_URL=http://127.0.0.1:8000

# 개발 중 허용할 프론트엔드 Origin 목록
# 여러 개일 경우 쉼표로 구분합니다.
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://172.16.102.164:3000
```

## 프론트엔드 실행 방법

```bash
cd nextjs-app
npm install
npm run dev
```

실행 후 브라우저에서 아래 주소로 접속합니다.

- http://localhost:3000
- 또는 네트워크 접속 시 현재 PC의 IP 주소 사용

## 백엔드 실행 방법

다른 터미널에서 FastAPI 서버를 실행하세요.

```powershell
cd ../fastapi-app
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

기본 백엔드 주소는 아래와 같습니다.

- http://127.0.0.1:8000

## Gemini CLI 브리지 실행 방법

백엔드가 Gemini CLI 모드를 사용한다면 브리지 서버도 별도 실행해야 합니다.

```powershell
cd ..
python .\gemini-cli-server.py
```

## 권장 실행 순서

1. FastAPI 백엔드 실행
2. Gemini CLI 브리지 실행 (사용 중일 때만)
3. Next.js 프론트엔드 실행

## 프론트엔드의 중요한 구성

- `src/app/page.tsx`
  - 메인 화면 진입점입니다.
- `src/hooks/usePPTGenerator.ts`
  - 문서 업로드, 생성 요청, 결과 표시, PPT 다운로드 흐름을 담당합니다.
- `src/lib/backend.ts`
  - 서버사이드에서 백엔드 주소를 결정하고 에러 응답을 정리합니다.
- `src/components/`
  - 업로드, 생성 상태, 결과 화면 등 UI 컴포넌트가 들어 있습니다.
- `src/types/api.ts`
  - 프론트엔드와 백엔드 간 API 타입 정의가 들어 있습니다.

## 중요한 변수명 정리

- `NEXT_PUBLIC_BACKEND_BASE_URL`
  - 브라우저에서 직접 FastAPI를 호출할 때 사용하는 주소입니다.
- `BACKEND_BASE_URL`
  - Next.js 서버 라우트에서 사용할 백엔드 주소입니다.
- `ALLOWED_ORIGINS`
  - 개발 환경에서 허용할 Origin 목록입니다.
- `allowedDevOrigins`
  - Next.js 개발 서버가 허용할 호스트 목록입니다. 현재 `ALLOWED_ORIGINS` 값을 바탕으로 자동 계산됩니다.
- `experimental.serverActions.allowedOrigins`
  - Server Actions 요청을 허용할 Origin 목록입니다.

## 문제 해결

- `NEXT_PUBLIC_BACKEND_BASE_URL 환경변수를 설정해주세요.`
  - `.env.local`에 `NEXT_PUBLIC_BACKEND_BASE_URL` 값을 추가하세요.

- `BACKEND_BASE_URL 또는 NEXT_PUBLIC_BACKEND_BASE_URL 환경변수를 설정해주세요.`
  - 두 값 중 하나 이상을 반드시 설정하세요.

- 생성 중 `fetch failed` 또는 timeout 발생
  - 백엔드가 실행 중인지 확인하고 `.env.local` 주소와 일치하는지 점검하세요.

- 브라우저에서 CORS 또는 cross-origin 오류 발생
  - `.env.local`의 `ALLOWED_ORIGINS`에 현재 접속 주소를 추가한 뒤 프론트엔드 서버를 재시작하세요.

- Gemini 관련 500 오류 발생
  - Gemini CLI 브리지 서버가 실행 중인지 확인하세요.
