# frontend/tests/test_api_client.py
import sys
import os
from unittest.mock import patch, MagicMock
import pytest
import httpx
import streamlit as st

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import api_client

@pytest.fixture(autouse=True)
def clear_session_state():
    """Clear st.session_state before each test."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    yield

def test_headers_empty_when_no_token():
    """Verify headers does not contain Authorization when token is absent."""
    headers = api_client._headers()
    assert "Authorization" not in headers

def test_headers_has_auth_when_token_present():
    """Verify headers contains Authorization when token is present."""
    st.session_state["token"] = "test-token-value"
    headers = api_client._headers()
    assert headers["Authorization"] == "Bearer test-token-value"

@patch("httpx.get")
def test_get_attaches_headers_and_returns_json(mock_get):
    """Verify GET request attaches correct headers and parses JSON."""
    st.session_state["token"] = "test-token"
    
    # Mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "ok"}
    mock_get.return_value = mock_resp
    
    result = api_client.get("/test-endpoint", params={"param1": "value1"})
    
    # Assertions
    mock_get.assert_called_once_with(
        f"{api_client.BASE_URL}/test-endpoint",
        headers={"Authorization": "Bearer test-token"},
        params={"param1": "value1"},
        timeout=10
    )
    mock_resp.raise_for_status.assert_called_once()
    assert result == {"status": "ok"}

@patch("httpx.post")
def test_post_attaches_headers_and_sends_json(mock_post):
    """Verify POST request attaches headers and sends JSON payload."""
    st.session_state["token"] = "test-token"
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 123}
    mock_post.return_value = mock_resp
    
    payload = {"title": "Test Item"}
    result = api_client.post("/items/", json=payload)
    
    mock_post.assert_called_once_with(
        f"{api_client.BASE_URL}/items/",
        headers={"Authorization": "Bearer test-token"},
        json=payload,
        timeout=10
    )
    mock_resp.raise_for_status.assert_called_once()
    assert result == {"id": 123}

@patch("httpx.post")
def test_login_sends_form_data(mock_post):
    """Verify login request sends form-encoded username/password data."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "token-123"}
    mock_post.return_value = mock_resp
    
    result = api_client.login("user@test.com", "password123")
    
    mock_post.assert_called_once_with(
        f"{api_client.BASE_URL}/api/auth/login",
        data={"username": "user@test.com", "password": "password123"},
        timeout=10
    )
    mock_resp.raise_for_status.assert_called_once()
    assert result == {"access_token": "token-123"}

@patch("httpx.get")
def test_get_propagates_status_error(mock_get):
    """Verify GET raises HTTPStatusError when raise_for_status fails."""
    mock_resp = MagicMock()
    # Mock raise_for_status to raise httpx.HTTPStatusError
    request = httpx.Request("GET", "http://localhost/test")
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Unauthorized",
        request=request,
        response=httpx.Response(401, request=request)
    )
    mock_get.return_value = mock_resp
    
    with pytest.raises(httpx.HTTPStatusError):
        api_client.get("/protected")
