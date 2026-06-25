from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from db import get_supabase_client

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/login")
async def login(body: LoginRequest, response: Response, supabase=Depends(get_supabase_client)):
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password
        })
        
        session = auth_response.session
        if not session:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Set HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=session.access_token,
            httponly=True,
            samesite="lax",
            max_age=session.expires_in
        )

        return {"status": "success", "user": auth_response.user.model_dump()}

    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        raise HTTPException(status_code=400, detail=error_msg)

import os
import psycopg2

@router.post("/register")
async def register(body: RegisterRequest, supabase=Depends(get_supabase_client)):
    try:
        auth_response = supabase.auth.sign_up({
            "email": body.email,
            "password": body.password,
            "options": {
                "data": {
                    "full_name": body.full_name,
                    "role": "Admin"  # Default role or configure as needed
                }
            }
        })
        
        # Auto-confirm the user via direct DB connection to bypass email confirmation
        db_url = os.getenv("PRICING_DATABASE_URL")
        if db_url and auth_response.user:
            try:
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE auth.users SET email_confirmed_at = NOW() WHERE id = %s",
                    (auth_response.user.id,)
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Warning: Auto-confirm failed: {e}")

        return {"status": "success", "user": auth_response.user.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, supabase=Depends(get_supabase_client)):
    try:
        # Supabase will send a reset password email if the user exists
        supabase.auth.reset_password_email(body.email)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/logout")
async def logout(response: Response, supabase=Depends(get_supabase_client)):
    try:
        # supabase.auth.sign_out() # Optional: Invalidates session on server
        response.delete_cookie("access_token")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me")
async def get_current_user(request: Request, supabase=Depends(get_supabase_client)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid session")
            
        return {
            "email": user.user.email,
            "full_name": user.user.user_metadata.get("full_name", "User"),
            "role": user.user.user_metadata.get("role", "Admin")
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
