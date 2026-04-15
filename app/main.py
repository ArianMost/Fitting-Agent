"""
app/main.py — FastAPI application factory.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from app.routers.assistant import router as assistant_router

app = FastAPI(
    title="Virtual Fitting Room API",
    description=(
        "AI-powered size recommendation agent built with PydanticAI. "
        "Send your body measurements and get back personalised size recommendations."
    ),
    version="1.0.0",
)

app.include_router(assistant_router)


@app.get("/", tags=["health"])
async def root() -> dict:
    return {"status": "ok", "service": "Virtual Fitting Room Agent"}


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)