# -*- coding: utf-8 -*-
"""이미 확보(임시예약)된 목표 열차를 기록해서, 프로그램을 껐다 켜도
같은 열차를 중복으로 예약 시도하지 않도록 한다."""
import json
import os

STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")


def load_secured() -> set:
    if not os.path.exists(STATE_PATH):
        return set()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("secured_target_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def mark_secured(target_id: str) -> None:
    secured = load_secured()
    secured.add(target_id)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"secured_target_ids": sorted(secured)}, f, ensure_ascii=False, indent=2)
