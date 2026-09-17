"""Supabase auth API. Generated from prompt-v1.md. Not edited afterwards."""

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Auth API", description="Supabase-backed authentication")

security = HTTPBearer()


class AuthRequest(BaseModel):
    email: str | None = None
    password: str | None = None


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


def get_current_user(authorization: str = Header(None)):
    """Extract the bearer token and verify it with Supabase."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Access token required")

    token = authorization.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        response = supabase.auth.get_user(token)
        user = response.user
        return {
            "id": str(user.id),
            "email": user.email,
            "created_at": str(user.created_at),
        }
    except Exception as e:
        print(f"Token verification failed for token {token}: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


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


@app.post("/auth/logout", status_code=204, dependencies=[Depends(security)])
async def logout(user=Depends(get_current_user)):
    supabase.auth.sign_out()
    return Response(status_code=204)


@app.get("/public/info")
async def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", dependencies=[Depends(security)])
async def profile(user=Depends(get_current_user)):
    return user


@app.get("/protected/dashboard", dependencies=[Depends(security)])
async def dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user['email']}!", "user": user}
