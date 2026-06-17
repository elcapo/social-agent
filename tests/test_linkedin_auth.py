from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from social_agent.cli.linkedin_auth import (
    _build_auth_url,
    _exchange_code,
    _save_to_env,
)


class TestAuthUrl:
    def test_build_auth_url_contains_required_params(self):
        url = _build_auth_url("client_123", "state_abc", "http://localhost:8080/callback")

        assert "response_type=code" in url
        assert "client_id=client_123" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback" in url
        assert "state=state_abc" in url
        assert "scope=" in url
        assert "openid" in url
        assert "profile" in url
        assert "w_member_social" in url

    def test_build_auth_url_with_custom_port(self):
        url = _build_auth_url("cid", "st", "http://localhost:9090/callback")
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A9090%2Fcallback" in url


class TestExchangeCode:
    @pytest.mark.asyncio
    async def test_exchange_code_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "AQV...token",
            "expires_in": 31536000,
        }

        with patch("social_agent.cli.linkedin_auth.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await _exchange_code("cid", "csecret", "the_code", "http://localhost:8080/callback")

        assert result["access_token"] == "AQV...token"
        assert result["expires_in"] == 31536000

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["grant_type"] == "authorization_code"
        assert call_kwargs["data"]["code"] == "the_code"
        assert "Basic" not in call_kwargs["headers"].get("Authorization", "")

    @pytest.mark.asyncio
    async def test_exchange_code_raises_on_http_error(self):
        with patch("social_agent.cli.linkedin_auth.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
                "400", request=MagicMock(), response=MagicMock(status_code=400),
            ))
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            import pytest
            with pytest.raises(httpx.HTTPStatusError):
                await _exchange_code("cid", "csecret", "bad_code", "http://localhost:8080/callback")


class TestSaveToEnv:
    def test_save_to_env_new_file(self, tmp_path):
        env_file = tmp_path / ".env"
        _save_to_env("AQV...token", str(env_file))
        content = env_file.read_text()
        assert "SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN=AQV...token" in content

    def test_save_to_env_replaces_existing(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN=old_token\nOTHER_VAR=1\n")
        _save_to_env("new_token", str(env_file))
        content = env_file.read_text()
        assert "SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN=new_token" in content
        assert "OTHER_VAR=1" in content
        assert "old_token" not in content

    def test_save_to_env_appends_when_not_found(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR=1\n")
        _save_to_env("token123", str(env_file))
        content = env_file.read_text()
        assert "SOCIAL_AGENT_LINKEDIN_ACCESS_TOKEN=token123" in content
        assert "OTHER_VAR=1" in content
