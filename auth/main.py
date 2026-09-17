"""A4, auth. Supabase is the identity provider, this server only checks its tokens.

The rule for the whole file: no password is ever stored here and nothing is ever hashed
here. Credentials go to Supabase, tokens come back, and this server verifies them.
"""

import contextlib
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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


# Declaring the scheme is what puts the padlock on the protected routes in Swagger and
# gives the Authorize button somewhere to put a token. auto_error=False so that a missing
# header produces this file's error shape rather than FastAPI's.
bearer = HTTPBearer(
    auto_error=False,
    bearerFormat="JWT",
    description="Paste the access_token returned by POST /auth/login.",
)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """One guard, standing at every locked door.

    Copy-pasting this check into each route is how a door ends up unguarded: miss one and
    nothing tells you. Every protected route depends on this function instead, so adding a
    route adds no auth code at all.
    """
    if credentials is None or not credentials.credentials.strip():
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        result = supabase.auth.get_user(credentials.credentials.strip())
    except AuthApiError as exc:
        raise HTTPException(401, "Invalid or expired token") from exc

    if result is None or result.user is None:
        raise HTTPException(401, "Invalid or expired token")

    return safe_user(result.user)


@app.get("/protected/profile")
async def profile(user: dict = Depends(current_user)) -> dict:
    """The route body only runs once the guard has verified the user."""
    return user


@app.get("/protected/dashboard")
async def dashboard(user: dict = Depends(current_user)) -> dict:
    """A second locked door, and not one line of new auth code. That reuse is the point."""
    return {"message": f"Welcome back, {user['email']}.", "user": user}


@app.post("/auth/logout", status_code=204)
async def logout(user: dict = Depends(current_user)) -> Response:
    """Protected: you have to prove who you are before you can stop being them."""
    supabase.auth.sign_out()
    return Response(status_code=204)
