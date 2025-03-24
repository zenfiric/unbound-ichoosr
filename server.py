"""Async server for handling agent queries and streaming responses."""

import json
import logging
import os
from typing import Any, AsyncGenerator

import aiofiles
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from igent import get_agents, get_history

# Load environment variables
load_dotenv(override=True)

# Initialize FastAPI app
app = FastAPI()

# Initialize router
router = APIRouter()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Environment variables
PORT = int(os.getenv("PORT", "8989"))
state_path = os.getenv("STATE_PATH", "static/agent_state.json")
history_path = os.getenv("HISTORY_PATH", "static/agent_history.json")
system_message = os.getenv("SYSTEM_MESSAGE", "You are a helpful assistant.")


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/history")
async def history() -> list[dict[str, Any]]:
    """Return the chat history."""
    try:
        return await get_history(history_path=history_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ask")
async def ask(prompt: TextMessage) -> StreamingResponse:
    """Endpoint to handle user prompts and stream agent output."""
    try:
        agent = await get_agents(state_path=state_path)
        response = await agent.on_messages(
            messages=[prompt], cancellation_token=CancellationToken()
        )

        # Save agent state to file.
        state = await agent.save_state()
        async with aiofiles.open(state_path, "w") as file:
            await file.write(json.dumps(state))

        async def sse_generator() -> AsyncGenerator[str, None]:
            """Generator to stream agent actions and results."""
            # Save chat history to file.
            history = await get_history(history_path=history_path)
            history.append(prompt.model_dump())
            history.append(response.chat_message.model_dump())
            async with aiofiles.open(history_path, "w") as file:
                await file.write(json.dumps(history))

            # assert isinstance(response.chat_message, TextMessage)
            yield f"{json.dumps(response.chat_message.model_dump())}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    except Exception as e:
        error_message = {
            "type": "error",
            "content": f"Error: {str(e)}",
            "source": "system",
        }
        raise HTTPException(status_code=500, detail=error_message) from e


# Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info("Incoming %s request to %s", request.method, request.url)
    response = await call_next(request)
    logger.info("Returning response with status code %s", response.status_code)
    return response


app.include_router(router, prefix="/ichoosr")
