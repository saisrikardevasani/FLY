"""A4, auth. Supabase is the identity provider, this server only checks its tokens.

The rule for the whole file: no password is ever stored here and nothing is ever hashed
here. Credentials go to Supabase, tokens come back, and this server verifies them.
"""

import contextlib
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import Client, create_client

load_dotenv()


def required(name: str) -> str:
    """Fail at startup with a readable message, not on the first request with a stack trace."""
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("your_") or "your-project-ref" in value:
        raise RuntimeError(
            f"{name} is missing from .env. Copy .env.example and fill in the real values "
            f"from Supabase Dashboard -> Project Settings -> API."
        )
    return value


SUPABASE_URL = required("SUPABASE_URL")
SUPABASE_KEY = required("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Server running and connected to Supabase at {SUPABASE_URL}", flush=True)
    yield


app = FastAPI(
    title="Auth API",
    version="1.0",
    description="Sign up, log in, log out, and one guarded door. Supabase holds the users.",
    lifespan=lifespan,
)
