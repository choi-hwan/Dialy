"""
인증 API 테스트
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestAuthRegister:
    """회원가입 테스트"""

    def test_register_success(self, client: TestClient):
        """정상적인 회원가입"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "newuser"
        assert data["user"]["email"] == "newuser@example.com"
        assert "id" in data["user"]
        assert "created_at" in data["user"]

    def test_register_duplicate_username(self, client: TestClient, test_user: dict):
        """중복된 사용자 이름으로 회원가입 시도"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": test_user["username"],
                "email": "another@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 400
        assert "이미 존재하는 사용자 이름" in response.json()["detail"]

    def test_register_duplicate_email(self, client: TestClient, test_user: dict):
        """중복된 이메일로 회원가입 시도"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "anotheruser",
                "email": test_user["email"],
                "password": "password123"
            }
        )

        assert response.status_code == 400
        assert "이미 등록된 이메일" in response.json()["detail"]

    def test_register_invalid_email(self, client: TestClient):
        """잘못된 이메일 형식"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "invalid-email",
                "password": "password123"
            }
        )

        assert response.status_code == 422  # Validation Error

    def test_register_short_password(self, client: TestClient):
        """너무 짧은 비밀번호"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "12345"  # 6자 미만
            }
        )

        assert response.status_code == 422  # Validation Error

    def test_register_short_username(self, client: TestClient):
        """너무 짧은 사용자 이름"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab",  # 3자 미만
                "email": "newuser@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 422  # Validation Error


class TestAuthLogin:
    """로그인 테스트"""

    def test_login_success(self, client: TestClient, test_user: dict):
        """정상적인 로그인"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == test_user["username"]
        assert data["user"]["email"] == test_user["email"]

    def test_login_wrong_password(self, client: TestClient, test_user: dict):
        """잘못된 비밀번호"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        assert "사용자 이름 또는 비밀번호가 올바르지 않습니다" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """존재하지 않는 사용자"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )

        assert response.status_code == 401
        assert "사용자 이름 또는 비밀번호가 올바르지 않습니다" in response.json()["detail"]

    def test_login_missing_fields(self, client: TestClient):
        """필수 필드 누락"""
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser"}  # password 누락
        )

        assert response.status_code == 422  # Validation Error
