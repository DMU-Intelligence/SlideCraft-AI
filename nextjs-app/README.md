# SlideCraft AI - Next.js client

Next.js UI for testing the SlideCraft AI FastAPI backend locally.

The presentation UI is based on **AI Presentation Generator UI** from [Figma](https://www.figma.com/design/eyDAHbNevAlfRz1P2e4C5G/AI-Presentation-Generator-UI). See [ATTRIBUTIONS.md](./ATTRIBUTIONS.md) for third-party credits.

## Requirements

- Node.js 20+
- npm 10+
- FastAPI backend repository (same workspace: `../fastapi-app`)

## 1) Environment Variables

This project no longer hardcodes backend URLs. You must configure env values before running.

Create `.env.local` in this folder (`nextjs-app/`) and add:

```env
# Browser-side calls from React hooks
NEXT_PUBLIC_BACKEND_BASE_URL=

# Optional: server-side proxy routes (/api/*)
# If omitted, NEXT_PUBLIC_BACKEND_BASE_URL is reused.
BACKEND_BASE_URL=
```

You can also copy from `.env.example` and rename it to `.env.local`.

## 2) Install And Run Frontend

```bash
npm install
npm run dev
```

Open http://localhost:3000

## 3) Run Backend (Required)

In another terminal:

```bash
cd ../fastapi-app
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Expected backend URL: http://127.0.0.1:8000

## 4) Optional: Gemini CLI Bridge

If your backend is configured to use Gemini CLI mode, run this in another terminal:

```bash
cd ..
python .\gemini-cli-server.py
```

## Run Order (Recommended)

1. Start FastAPI backend
2. Start Gemini CLI bridge (if using `LLM_MODE=gemini-cli`)
3. Start Next.js frontend

## Troubleshooting

- Error: `NEXT_PUBLIC_BACKEND_BASE_URL 환경변수를 설정해주세요.`
	- Create `.env.local` and set `NEXT_PUBLIC_BACKEND_BASE_URL`.

- Error: `BACKEND_BASE_URL 또는 NEXT_PUBLIC_BACKEND_BASE_URL 환경변수를 설정해주세요.`
	- Set at least one of `BACKEND_BASE_URL` or `NEXT_PUBLIC_BACKEND_BASE_URL`.

- `fetch failed` or timeout during generation
	- Verify backend is running and URL matches `.env.local`.
	- Check backend logs in `fastapi-app` terminal.

- CORS issue in browser
	- Ensure backend CORS settings allow the frontend origin (for example `http://localhost:3000`).
