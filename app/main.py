"""FastAPI app: ask a question, get an answer researched with web search.

Endpoints
  GET  /health            health check for App Service
  POST /api/ask           {"question": "..."} -> {"answer", "sources", "cost_usd"}
  GET  /api/ask/stream    ?question=...  Server-Sent Events: progress, then answer
  GET  /                  simple test page
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agent import answer, stream_answer
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("app")

app = FastAPI(title="Web search agent (Claude Agent SDK)", version="0.1.0")
_slots = asyncio.Semaphore(settings.max_concurrent)
_STATIC = Path(__file__).parent / "static"


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          examples=["What is the score in today's India vs New Zealand match?"])


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    cost_usd: float | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.post("/api/ask", response_model=AskResponse)
async def ask(body: AskRequest) -> AskResponse:
    if _slots.locked():
        raise HTTPException(status_code=503, detail="Busy. Try again in a moment.")
    async with _slots:
        try:
            result = await asyncio.wait_for(answer(body.question), timeout=settings.timeout_seconds)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="The search took too long. Try a narrower question.")
        except Exception as exc:  # noqa: BLE001
            log.exception("ask failed")
            raise HTTPException(status_code=502, detail=f"Agent error: {exc}") from exc
    return AskResponse(answer=result["answer"], sources=result["sources"], cost_usd=result["cost_usd"])


@app.get("/api/ask/stream")
async def ask_stream(question: str = Query(..., min_length=3, max_length=500)) -> StreamingResponse:
    if _slots.locked():
        raise HTTPException(status_code=503, detail="Busy. Try again in a moment.")

    async def events():
        async with _slots:
            try:
                async with asyncio.timeout(settings.timeout_seconds):
                    async for event in stream_answer(question):
                        yield f"event: {event['kind']}\ndata: {json.dumps(event)}\n\n"
            except TimeoutError:
                yield _sse_error("The search took too long. Try a narrower question.")
            except Exception as exc:  # noqa: BLE001
                log.exception("stream failed")
                yield _sse_error(f"Agent error: {exc}")

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_error(message: str) -> str:
    return f"event: error\ndata: {json.dumps({'kind': 'error', 'message': message})}\n\n"



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
