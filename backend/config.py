"""
config.py — Environment variable loading for Music AI Chatbot.
Reads all secrets from .env (local) or Railway environment (production).
Import this module wherever you need API keys or environment settings.
"""
import os
from dotenv import load_dotenv

# Load .env file when running locally.
# On Railway, environment variables are injected directly — load_dotenv() is a no-op there.
load_dotenv()

# --- OpenAI ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# --- xAI (Grok) ---
XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")
GROK_MODEL: str = "grok-4.3"
GROK_REASONING_EFFORT: str = "medium"
GROK_TEMPERATURE: float = 0.7

# --- Spotify ---
SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# --- AssemblyAI ---
ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")

# --- Supabase ---
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

# --- LangSmith ---
LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", LANGCHAIN_API_KEY)
LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "false")
LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "music-ai-chatbot")

# --- Environment mode ---
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")

# --- Derived flags ---
IS_PRODUCTION: bool = ENVIRONMENT == "production"


# --- Startup validation ---
def validate_config() -> None:
    """
    Check that all required environment variables are set.
    Called once at app startup. Raises ValueError on missing keys.
    """
    required = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "SPOTIFY_CLIENT_ID": SPOTIFY_CLIENT_ID,
        "SPOTIFY_CLIENT_SECRET": SPOTIFY_CLIENT_SECRET,
        "ASSEMBLYAI_API_KEY": ASSEMBLYAI_API_KEY,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            f"[config] Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your values."
        )

    # Warn if Grok key is missing (not required to start, but needed for marketing features)
    if not XAI_API_KEY:
        print("[config] WARNING: XAI_API_KEY not set — Grok features will not work")
    else:
        print(f"[config] Grok model: {GROK_MODEL} (reasoning: {GROK_REASONING_EFFORT}) ✓")

    print(f"[config] Environment: {ENVIRONMENT}")
    print(f"[config] LangSmith tracing: {LANGCHAIN_TRACING_V2}")
    print("[config] All required environment variables loaded ✓")