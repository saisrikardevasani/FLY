"""A4, auth. Supabase is the identity provider, this server only checks its tokens.

The rule for the whole file: no password is ever stored here and nothing is ever hashed
here. Credentials go to Supabase, tokens come back, and this server verifies them.
"""

import contextlib
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from supabase import AuthApiError, Client, create_client

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


class Credentials(BaseModel):
    """Email and password go straight to Supabase and are never stored here.

    The golden rule for this whole file: no password is written down and nothing is
    hashed locally. Supabase does that, and this server only ever checks its tokens.
    """

    email: EmailStr
    password: str = Field(min_length=1)


@app.exception_handler(RequestValidationError)
async def invalid_body(request, exc: RequestValidationError) -> JSONResponse:
    """A missing or malformed field is the client's mistake: 400, naming the field."""
    problem = exc.errors()[0]
    field = ".".join(p for p in problem["loc"][1:] if isinstance(p, str)) or "body"
    return JSONResponse(status_code=400, content={"error": f"{field}: {problem['msg']}"})


@app.exception_handler(HTTPException)
async def error_shape(request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


def safe_user(user) -> dict:
    """Only the fields a client needs. The rest of Supabase's user object stays here."""
    return {
        "id": str(user.id),
        "email": user.email,
        "created_at": str(user.created_at),
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/signup", status_code=201)
async def signup(body: Credentials) -> dict:
    """Create the account at Supabase. This server never sees a stored password."""
    try:
        result = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as exc:
        # Supabase rejects weak passwords and already-registered emails. Both are the
        # caller's problem to fix, so pass the reason through rather than a bare 500.
        raise HTTPException(status_code=400, detail=exc.message) from exc

    if result.user is None:
        raise HTTPException(status_code=400, detail="Supabase did not create a user")
    return safe_user(result.user)


@app.post("/auth/login")
async def login(body: Credentials) -> dict:
    """Exchange credentials for a token. Supabase decides, this server just relays."""
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as exc:
        # 401 means "I do not know you". Never say which half was wrong: that tells an
        # attacker which email addresses exist.
        raise HTTPException(status_code=401, detail="Invalid login credentials") from exc

    if result.session is None:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
        "expires_in": result.session.expires_in,
        "user": safe_user(result.user),
    }


@app.get("/public/info")
async def public_info() -> dict:
    """The lobby. No token, no questions."""
    return {"message": "Welcome stranger! This info is public."}


def token_from(authorization: str | None) -> str:
    """Pull the token out of an Authorization header, or refuse the request.

    The header has to be exactly "Bearer <token>". A bare token with no scheme, or a
    scheme with nothing after it, is malformed and gets the same 401 as no header at all.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Access token required")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Access token required")
    return token.strip()


@app.get("/protected/profile")
async def profile(authorization: str | None = Header(default=None)) -> dict:
    """The guard inspects the pass, and turns away forgeries.

    Verification is a network call to Supabase rather than a local check, which is the
    point: this server cannot be talked into accepting a token Supabase would reject.
    """
    token = token_from(authorization)

    try:
        result = supabase.auth.get_user(token)
    except AuthApiError as exc:
        raise HTTPException(401, "Invalid or expired token") from exc

    if result is None or result.user is None:
        raise HTTPException(401, "Invalid or expired token")

    return safe_user(result.user)
