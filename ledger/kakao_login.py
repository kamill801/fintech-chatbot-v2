from __future__ import annotations

import re
from urllib.parse import urlencode

import requests


class KakaoLoginError(Exception):
    pass


_STATE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_NONCE_HASH = re.compile(r"^[0-9a-f]{64}$")
_CODE = re.compile(r"^[\x21-\x7e]{1,1024}$")
_PKCE_CHALLENGE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_PKCE_VERIFIER = re.compile(r"^[A-Za-z0-9_-]{43,128}$")


def authorization_url(
    client_id: str, origin: str, state: str, nonce_hash: str, code_challenge: str
) -> str:
    if (not client_id or not _STATE.fullmatch(state) or not _NONCE_HASH.fullmatch(nonce_hash)
            or not _PKCE_CHALLENGE.fullmatch(code_challenge)):
        raise KakaoLoginError("invalid Kakao login request")
    query = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": f"{origin}/auth/kakao",
        "state": state,
        "nonce": nonce_hash,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return f"https://kauth.kakao.com/oauth/authorize?{query}"


def exchange_code(
    client_id: str, client_secret: str, origin: str, code: str, code_verifier: str
) -> str:
    if not client_id or not client_secret:
        raise KakaoLoginError("Kakao login is not configured")
    if (not isinstance(code, str) or not _CODE.fullmatch(code)
            or not isinstance(code_verifier, str) or not _PKCE_VERIFIER.fullmatch(code_verifier)):
        raise KakaoLoginError("invalid Kakao authorization code")
    try:
        response = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": f"{origin}/auth/kakao",
                "code": code,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
            timeout=10,
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as error:
        raise KakaoLoginError("Kakao token exchange failed") from error
    token = payload.get("id_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token:
        raise KakaoLoginError("Kakao did not issue an ID token")
    return token
