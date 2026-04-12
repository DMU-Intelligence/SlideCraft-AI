"""
GPT CLI 브릿지 서버

서버 시작 시 Codex app-server 프로세스를 한 번 실행하고,
이후 모든 API 요청은 같은 프로세스/같은 스레드에 전달합니다.

실행:
    python gpt-cli-server.py

환경 변수:
    CLI_COMMAND         : 실행할 CLI 명령어 (기본값: codex app-server)
    CLI_SERVER_PORT     : 서버 포트 (기본값: 5001)
    CLI_TIMEOUT_SECONDS : Codex 응답 대기 시간 초 (기본값: 300)
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
logger = logging.getLogger("gpt-cli-bridge")

DEFAULT_CLI_COMMAND = "codex app-server"

app = FastAPI(title="GPT CLI Bridge Server")


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    response: str
    thread_id: str


class PromptJob:
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.done = threading.Event()
        self.response: Optional[str] = None
        self.error: Optional[str] = None


class CodexAppServerClient:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.thread_id: Optional[str] = None
        self.initialized = False
        self.timeout_seconds = int(os.getenv("CLI_TIMEOUT_SECONDS", "300"))
        self.command = os.getenv("CLI_COMMAND", DEFAULT_CLI_COMMAND)
        self.cwd = os.getcwd()
        self.jobs: "queue.Queue[PromptJob]" = queue.Queue()
        self.request_ids = count(1)
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.stderr_thread: Optional[threading.Thread] = None

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
            raise HTTPException(status_code=502, detail="Codex 응답 본문을 찾지 못했습니다.")

        return job.response

    def _worker_loop(self) -> None:
        try:
            self._start_process()
            self._initialize_connection()
            self._start_thread()

            while True:
                job = self.jobs.get()
                try:
                    job.response = self._run_turn(job.prompt)
                except Exception as exc:
                    job.error = str(exc)
                finally:
                    job.done.set()
        except Exception as exc:
            logger.exception("[SESSION] worker failed: %s", exc)
            while not self.jobs.empty():
                job = self.jobs.get_nowait()
                job.error = str(exc)
                job.done.set()

    def _start_process(self) -> None:
        logger.info("[SESSION] starting app-server: %s", self.command)
        self.process = subprocess.Popen(
            ["cmd", "/c", self.command],
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
        params = {
            "clientInfo": {"name": "gpt-cli-bridge", "version": "1.0.0"},
            "capabilities": {},
        }
        self._request("initialize", params)
        self.initialized = True
        logger.info("[SESSION] app-server initialized")

    def _start_thread(self) -> None:
        params = {
            "cwd": self.cwd,
            "serviceName": "gpt-cli-bridge",
            "personality": "pragmatic",
        }
        result = self._request("thread/start", params)
        thread = (result or {}).get("thread") or {}
        self.thread_id = thread.get("id")
        if not self.thread_id:
            raise RuntimeError("Codex thread id를 받지 못했습니다.")
        logger.info("[SESSION] thread started: %s", self.thread_id)

    def _run_turn(self, prompt: str) -> str:
        if not self.thread_id:
            raise RuntimeError("Codex thread가 초기화되지 않았습니다.")

        request_id = next(self.request_ids)
        payload = {
            "id": request_id,
            "method": "turn/start",
            "params": {
                "threadId": self.thread_id,
                "input": [{"type": "text", "text": prompt}],
            },
        }
        self._send_message(payload)

        response_text = ""
        final_response_text = ""
        turn_id = None
        deadline = time.time() + self.timeout_seconds

        while time.time() < deadline:
            message = self._read_message(deadline)
            if not message:
                continue

            if message.get("id") == request_id:
                error = message.get("error")
                if error:
                    raise RuntimeError(json.dumps(error, ensure_ascii=False))
                result = message.get("result") or {}
                turn = result.get("turn") or {}
                turn_id = turn.get("id") or turn_id
                continue

            method = message.get("method")
            params = message.get("params") or {}

            if method == "item/completed":
                item = params.get("item") or {}
                text, is_final = self._extract_agent_text(item)
                if text:
                    response_text = text
                    if is_final:
                        final_response_text = text
                continue

            if method == "turn/completed":
                completed_turn = (params.get("turn") or {}).get("id")
                if turn_id is None or completed_turn == turn_id:
                    if final_response_text:
                        return final_response_text
                    if response_text:
                        return response_text
                    raise RuntimeError("Codex 응답 본문을 찾지 못했습니다.")

            if method == "error":
                raise RuntimeError(json.dumps(params, ensure_ascii=False))

        raise RuntimeError(f"CLI 명령어 타임아웃 ({self.timeout_seconds}초)")

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = next(self.request_ids)
        payload = {"id": request_id, "method": method, "params": params}
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
            raise RuntimeError("Codex app-server 프로세스가 없습니다.")

        body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.process.stdin.write(body)
        self.process.stdin.flush()

    def _read_message(self, deadline: float) -> Optional[dict[str, Any]]:
        if not self.process or not self.process.stdout:
            raise RuntimeError("Codex app-server 출력 스트림이 없습니다.")

        while time.time() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"Codex app-server 종료됨 (exit code {self.process.returncode})"
                )

            line = self.process.stdout.readline()
            if not line:
                continue

            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue

            return json.loads(text)

        return None

    @staticmethod
    def _extract_agent_text(item: dict[str, Any]) -> tuple[str, bool]:
        if item.get("type") != "agentMessage":
            return "", False

        text = item.get("text")
        phase = item.get("phase")
        if isinstance(text, str) and text.strip():
            return text.strip(), phase == "final_answer"

        return "", False


client = CodexAppServerClient()


@app.on_event("startup")
def startup_event():
    client.start()


@app.on_event("shutdown")
def shutdown_event():
    client.stop()


@app.post("/generate", response_model=PromptResponse)
def generate(req: PromptRequest):
    logger.info(
        "[REQUEST] /generate received (thread_id=%s, prompt_chars=%d)",
        client.thread_id,
        len(req.prompt),
    )
    response_text = client.ask(req.prompt)
    return PromptResponse(response=response_text, thread_id=client.thread_id or "")


@app.get("/health")
def health():
    return {
        "status": "ok" if client.initialized and client.thread_id else "starting",
        "cli_command": client.command,
        "thread_id": client.thread_id,
    }


if __name__ == "__main__":
    port = int(os.getenv("CLI_SERVER_PORT", "5001"))
    print(f"GPT CLI Bridge Server starting on port {port}")
    print(f"CLI_COMMAND = {client.command}")
    uvicorn.run(app, host="0.0.0.0", port=port)
