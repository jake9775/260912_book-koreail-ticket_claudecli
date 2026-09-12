# -*- coding: utf-8 -*-
"""
코레일 로그인 정보를 OS 자격 증명 관리자(Windows Credential Manager 등)에
암호화 저장/조회한다. 평문 파일이나 소스코드에는 절대 저장하지 않는다.
"""
import keyring
import keyring.errors

SERVICE_NAME = "korail_ticket_assistant"
KEY_ID = "korail_id"
KEY_PW = "korail_pw"


def save_credentials(korail_id: str, korail_pw: str) -> None:
    keyring.set_password(SERVICE_NAME, KEY_ID, korail_id)
    keyring.set_password(SERVICE_NAME, KEY_PW, korail_pw)


def load_credentials():
    """저장된 (아이디, 비밀번호)를 반환한다. 없으면 (None, None)."""
    korail_id = keyring.get_password(SERVICE_NAME, KEY_ID)
    korail_pw = keyring.get_password(SERVICE_NAME, KEY_PW)
    return korail_id, korail_pw


def has_credentials() -> bool:
    korail_id, korail_pw = load_credentials()
    return bool(korail_id and korail_pw)


def clear_credentials() -> None:
    for key in (KEY_ID, KEY_PW):
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except keyring.errors.PasswordDeleteError:
            pass
