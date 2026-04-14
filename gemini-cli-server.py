"""
Gemini / GPT CLI 브릿지 서버

서버 시작 시 Gemini CLI ACP 프로세스를 한 번 실행하고,
이후 모든 API 요청은 같은 프로세스/같은 대화 컨텍스트에 전달합니다.

실행:
    python gemini-cli-server.py

환경 변수:
    CLI_COMMAND         : 실행할 CLI 명령어 (기본값: gemini)
    CLI_SERVER_PORT     : 서버 포트 (기본값: 5001)
    CLI_TIMEOUT_SECONDS : Gemini 응답 대기 시간 초 (기본값: 300)
"""
import json
import logging
import os
import queue
import subprocess
import threading
import time
from itertools import count
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cli-bridge")

DEFAULT_CLI_COMMAND = "gemini"
ACP_PROTOCOL_VERSION = 1

app = FastAPI(title="CLI Bridge Server")


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    response: str


class PromptJob:
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.done = threading.Event()
        self.response: Optional[str] = None
        self.error: Optional[str] = None


class GeminiACPClient:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.session_id: Optional[str] = None
        self.initialized = False
        self.timeout_seconds = int(os.getenv("CLI_TIMEOUT_SECONDS", "300"))
        self.command = os.getenv("CLI_COMMAND", DEFAULT_CLI_COMMAND)
        self.actual_command = self._build_command(self.command)
        self.cwd = os.getcwd()
        self.jobs: "queue.Queue[PromptJob]" = queue.Queue()
        self.request_ids = count(1)
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.stderr_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self.worker_thread.is_alive():
            return
        self.worker_thread.start()

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def ask(self, prompt: str) -> str:
        job = PromptJob(prompt)
        self.jobs.put(job)

        if not job.done.wait(self.timeout_seconds):
            raise HTTPException(
                status_code=504,
                detail=f"CLI 명령어 타임아웃 ({self.timeout_seconds}초)",
            )

        if job.error:
            raise HTTPException(status_code=502, detail=job.error)

        if job.response is None:
            raise HTTPException(status_code=502, detail="Gemini 응답 본문을 찾지 못했습니다.")

        return job.response

    def _worker_loop(self) -> None:
        try:
            self._start_process()
            self._initialize_connection()
            self._create_session()

            while True:
                job = self.jobs.get()
                try:
                    job.response = self._run_turn(job.prompt)
                except Exception as exc:
                    logger.exception("[SESSION] request failed: %s", exc)
                    job.error = str(exc)
                finally:
                    job.done.set()
        except Exception as exc:
            logger.exception("[SESSION] worker failed: %s", exc)
            while not self.jobs.empty():
                job = self.jobs.get_nowait()
                job.error = str(exc)
                job.done.set()

    def _build_command(self, command: str) -> list[str]:
        command = command.strip() or DEFAULT_CLI_COMMAND
        if "--acp" not in command:
            command = f"{command} --acp"
        return ["cmd", "/c", command]

    def _start_process(self) -> None:
        logger.info("[SESSION] starting gemini ACP: %s", " ".join(self.actual_command))
        self.process = subprocess.Popen(
            self.actual_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            bufsize=0,
        )
        self.stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self.stderr_thread.start()

    def _drain_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return

        while True:
            line = self.process.stderr.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                logger.warning("[CLI] %s", text)

    def _initialize_connection(self) -> None:
        result = self._request(
            "initialize",
            {
                "protocolVersion": ACP_PROTOCOL_VERSION,
                "clientCapabilities": {
                    "fs": {"readTextFile": False, "writeTextFile": False},
                    "terminal": False,
                    "auth": {"terminal": False},
                },
                "clientInfo": {"name": "gemini-cli-bridge", "version": "1.0.0"},
            },
        )
        self.initialized = True
        logger.info("[SESSION] gemini ACP initialized: %s", json.dumps(result, ensure_ascii=False))

    def _create_session(self) -> None:
        result = self._request(
            "session/new",
            {
                "cwd": self.cwd,
                "mcpServers": [],
            },
        )
        self.session_id = result.get("sessionId")
        if not self.session_id:
            raise RuntimeError("Gemini sessionId를 받지 못했습니다.")
        logger.info("[SESSION] created session: %s", self.session_id)

    def _run_turn(self, prompt: str) -> str:
        if not self.session_id:
            raise RuntimeError("Gemini session이 초기화되지 않았습니다.")

        request_id = next(self.request_ids)
        message_id = f"msg-{request_id}"
        payload = {
            "id": request_id,
            "method": "session/prompt",
            "params": {
                "sessionId": self.session_id,
                "messageId": message_id,
                "prompt": [{"type": "text", "text": prompt}],
            },
        }

        with self._lock:
            self._send_message(payload)
            deadline = time.time() + self.timeout_seconds
            chunks: list[str] = []
            saw_result = False

            while time.time() < deadline:
                message = self._read_message(deadline)
                if not message:
                    continue

                if message.get("id") == request_id:
                    error = message.get("error")
                    if error:
                        raise RuntimeError(json.dumps(error, ensure_ascii=False))
                    saw_result = True
                    if chunks:
                        return "".join(chunks).strip()
                    continue

                if message.get("method") != "session/update":
                    continue

                params = message.get("params") or {}
                if params.get("sessionId") != self.session_id:
                    continue

                update = params.get("update") or {}
                update_type = update.get("sessionUpdate")
                if update_type == "agent_message_chunk":
                    text = self._content_block_to_text(update.get("content") or {})
                    if text:
                        chunks.append(text)
                elif update_type == "tool_call":
                    logger.info("[SESSION] tool call requested during prompt")
                elif update_type == "tool_call_update":
                    logger.info("[SESSION] tool call update received")

                if saw_result and chunks:
                    return "".join(chunks).strip()

        raise RuntimeError(f"session/prompt 타임아웃 ({self.timeout_seconds}초)")

    def _content_block_to_text(self, block: dict[str, Any]) -> str:
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text")
            return text if isinstance(text, str) else ""
        if block_type == "resource":
            resource = block.get("resource") or {}
            return resource.get("text") or ""
        return ""

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = next(self.request_ids)
        payload = {
            "id": request_id,
            "method": method,
            "params": params,
        }
        with self._lock:
            self._send_message(payload)
            deadline = time.time() + self.timeout_seconds
            while time.time() < deadline:
                message = self._read_message(deadline)
                if not message:
                    continue

                if message.get("id") != request_id:
                    continue

                error = message.get("error")
                if error:
                    raise RuntimeError(json.dumps(error, ensure_ascii=False))

                return message.get("result") or {}

        raise RuntimeError(f"{method} 타임아웃 ({self.timeout_seconds}초)")

    def _send_message(self, payload: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise RuntimeError("Gemini ACP 프로세스가 없습니다.")

        body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.process.stdin.write(body)
        self.process.stdin.flush()

    def _read_message(self, deadline: float) -> Optional[dict[str, Any]]:
        if not self.process or not self.process.stdout:
            raise RuntimeError("Gemini ACP 출력 스트림이 없습니다.")

        while time.time() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"Gemini ACP 종료됨 (exit code {self.process.returncode})"
                )

            line = self.process.stdout.readline()
            if not line:
                continue

            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue

            return json.loads(text)

        return None


client = GeminiACPClient()


@app.on_event("startup")
def startup_event():
    client.start()


@app.on_event("shutdown")
def shutdown_event():
    client.stop()


@app.post("/generate", response_model=PromptResponse)
def generate(req: PromptRequest):
    logger.info(
        "[REQUEST] /generate received (session_id=%s, prompt_chars=%d)",
        client.session_id,
        len(req.prompt),
    )
    response_text = client.ask(req.prompt)
    return PromptResponse(response=response_text)


@app.get("/health")
def health():
    return {
        "status": "ok" if client.initialized else "starting",
        "cli_command": client.command,
    }


if __name__ == "__main__":
    port = int(os.getenv("CLI_SERVER_PORT", "5001"))
    print(f"CLI Bridge Server starting on port {port}")
    print(f"CLI_COMMAND = {client.command}")
    uvicorn.run(app, host="0.0.0.0", port=port)
