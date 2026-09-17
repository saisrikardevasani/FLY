"""Supabase auth API, v2. Generated from prompt-v2.md. Not edited afterwards."""

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import AuthApiError, Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Auth API", description="Supabase-backed authentication")

# auto_error=False so this file decides the shape of the 401, not FastAPI.
security = HTTPBearer(auto_error=False, bearerFormat="JWT")


class AuthRequest(BaseModel):
    email: str | None = None
    password: str | None = None


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """Verify the bearer token with Supabase.

    The scheme is parsed rather than stripped, and compared case-insensitively, because
    RFC 7235 says the scheme is case-insensitive. The token is never logged: it is a
    credential, and a log line holding one is a credential in a log.
    """
    if credentials is None or not credentials.credentials.strip():
        raise HTTPException(status_code=401, detail="Access token required")

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Access token required")

    token = credentials.credentials.strip()

    try:
        response = supabase.auth.get_user(token)
    except AuthApiError as e:
        # The reason, never the token.
        print(f"Token verification failed (...{token[-6:]}): {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if response is None or response.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = response.user
    return {
        "id": str(user.id),
        "email": user.email,
        "created_at": str(user.created_at),
    }


@app.post("/auth/signup", status_code=201)
async def signup(body: AuthRequest):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = supabase.auth.sign_up({"email": body.email, "password": body.password})
        return {
            "id": str(result.user.id),
            "email": result.user.email,
            "created_at": str(result.user.created_at),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
async def login(body: AuthRequest):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    try:
        result = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
        "token_type": "bearer",
    }


@app.post("/auth/logout", status_code=204)
async def logout(user=Depends(get_current_user)):
    supabase.auth.sign_out()
    return Response(status_code=204)


@app.get("/public/info")
async def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
async def profile(user=Depends(get_current_user)):
    return user


@app.get("/protected/dashboard")
async def dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user['email']}!", "user": user}
