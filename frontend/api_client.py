import os
import httpx
import streamlit as st
from typing import Any, Optional

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def _headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def get(path: str, params: Optional[dict] = None) -> Any:
    resp = httpx.get(f"{BASE_URL}{path}", headers=_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def post(path: str, json: dict) -> Any:
    resp = httpx.post(f"{BASE_URL}{path}", headers=_headers(), json=json, timeout=10)
    resp.raise_for_status()
    return resp.json()

def login(username, password) -> Any:
    resp = httpx.post(f"{BASE_URL}/api/auth/login", data={"username": username, "password": password}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def patch(path: str, json: Optional[dict] = None) -> Any:
    resp = httpx.patch(f"{BASE_URL}{path}", headers=_headers(), json=json or {}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def delete(path: str) -> Any:
    resp = httpx.delete(f"{BASE_URL}{path}", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()
