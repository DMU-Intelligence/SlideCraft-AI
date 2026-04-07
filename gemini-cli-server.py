"""
Gemini / GPT CLI 브릿지 서버

CLI 도구를 subprocess로 호출하고, 결과를 HTTP JSON으로 반환합니다.
FastAPI 앱(port 8000)이 이 서버(port 5001)를 호출하여 LLM 응답을 받습니다.

실행:
    python gemini-cli-server.py

환경 변수:
    CLI_COMMAND      : 실행할 CLI 명령어 (기본값: gemini)
    CLI_SERVER_PORT  : 서버 포트 (기본값: 5001)
"""
import os
import subprocess
import sys

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cli-bridge")

app = FastAPI(title="CLI Bridge Server")


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    response: str


@app.post("/generate", response_model=PromptResponse)
def generate(req: PromptRequest):
    """CLI 도구에 프롬프트를 전달하고 응답을 반환합니다."""
    cmd = os.getenv("CLI_COMMAND", "gemini")

    logger.info("=" * 50)
    logger.info("[REQUEST] 프롬프트 수신 (%d자)", len(req.prompt))
    logger.info("[REQUEST] 프롬프트 앞부분: %s", req.prompt[:200])
    logger.info("[REQUEST] CLI 명령어: %s", cmd)

    try:
        if sys.platform == "win32":
            result = subprocess.run(
                cmd,
                input=req.prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=True,
                timeout=300,
            )
        else:
            result = subprocess.run(
                cmd.split(),
                input=req.prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )
    except subprocess.TimeoutExpired:
        logger.error("[ERROR] CLI 타임아웃 (300초)")
        raise HTTPException(status_code=504, detail="CLI 명령어 타임아웃 (300초)")
    except FileNotFoundError:
        logger.error("[ERROR] CLI 명령어를 찾을 수 없음: %s", cmd)
        raise HTTPException(
            status_code=500,
            detail=f"CLI 명령어를 찾을 수 없습니다: {cmd}",
        )

    logger.info("[CLI] exit code: %d", result.returncode)
    logger.info("[CLI] stdout (%d자): %s", len(result.stdout or ""), (result.stdout or "")[:300])
    if result.stderr:
        logger.warning("[CLI] stderr: %s", result.stderr[:300])

    if result.returncode != 0:
        logger.error("[ERROR] CLI 비정상 종료 (exit code %d)", result.returncode)
        raise HTTPException(
            status_code=502,
            detail=(
                f"CLI 오류 (exit code {result.returncode}). "
                f"Stderr: {(result.stderr or '')[:500]}"
            ),
        )

    response_text = result.stdout.strip()
    logger.info("[RESPONSE] 응답 길이: %d자", len(response_text))
    logger.info("[RESPONSE] 응답 앞부분: %s", response_text[:200])
    logger.info("=" * 50)

    return PromptResponse(response=response_text)


@app.get("/health")
def health():
    cmd = os.getenv("CLI_COMMAND", "gemini")
    return {"status": "ok", "cli_command": cmd}


if __name__ == "__main__":
    port = int(os.getenv("CLI_SERVER_PORT", "5001"))
    print(f"CLI Bridge Server starting on port {port}")
    print(f"CLI_COMMAND = {os.getenv('CLI_COMMAND', 'gemini')}")
    uvicorn.run(app, host="0.0.0.0", port=port)
