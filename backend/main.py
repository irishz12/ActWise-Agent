from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.graph_agent import (
    resume_graph_agent,
    run_graph_agent,
)


app = FastAPI(
    title="ActWise Agent API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    clarification: str


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "actwise-agent",
    }


@app.post("/agent/run")
def run_agent(request: RunRequest):
    thread_id = request.thread_id or str(uuid4())

    result = run_graph_agent(
        request.message,
        thread_id=thread_id,
    )

    interrupts = result.get("__interrupt__", [])

    return {
        "thread_id": thread_id,
        "decision": result.get("decision"),
        "answer": result.get("answer"),
        "paused": bool(interrupts),
        "interrupt": (
            interrupts[0].value
            if interrupts
            else None
        ),
        "tool_history": result.get(
            "tool_history",
            [],
        ),
        "skipped_calls": result.get(
            "skipped_calls",
            [],
        ),
        "decision_history": result.get(
            "decision_history",
            [],
        ),
    }


@app.post("/agent/resume")
def resume_agent(request: ResumeRequest):
    result = resume_graph_agent(
        request.clarification,
        thread_id=request.thread_id,
    )

    interrupts = result.get("__interrupt__", [])

    return {
        "thread_id": request.thread_id,
        "decision": result.get("decision"),
        "answer": result.get("answer"),
        "paused": bool(interrupts),
        "interrupt": (
            interrupts[0].value
            if interrupts
            else None
        ),
        "tool_history": result.get(
            "tool_history",
            [],
        ),
        "skipped_calls": result.get(
            "skipped_calls",
            [],
        ),
        "decision_history": result.get(
            "decision_history",
            [],
        ),
    }
