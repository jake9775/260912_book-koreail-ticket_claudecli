# -*- coding: utf-8 -*-
"""korail2 라이브러리를 감싸서, 설정 파일의 조건들을 조회/예약하는 기능을 제공한다.
브라우저 화면을 긁는 대신 코레일 공식 모바일 앱과 같은 방식(API)으로 통신하므로
사이트 디자인이 바뀌어도 잘 깨지지 않는다."""
from datetime import datetime, timedelta

from korail2 import Korail, AdultPassenger, ReserveOption, NoResultsError

STATUS_SOLDOUT = "매진"
STATUS_AVAILABLE = "좌석있음"
STATUS_ERROR_PREFIX = "오류"


def _time_minus_minutes(hhmmss: str, minutes: int) -> str:
    t = datetime.strptime(hhmmss, "%H%M%S")
    t = t - timedelta(minutes=minutes)
    return t.strftime("%H%M%S")


class KorailClient:
    """코레일 로그인 세션을 유지하며 조건별 조회/예약을 수행한다."""

    def __init__(self, korail_id: str, korail_pw: str):
        self._id = korail_id
        self._pw = korail_pw
        self._korail = None

    def ensure_login(self) -> bool:
        if self._korail is not None and self._korail.logined:
            return True
        try:
            self._korail = Korail(self._id, self._pw, auto_login=True)
        except Exception:
            self._korail = None
            return False
        return bool(self._korail and self._korail.logined)

    def check_target(self, group: dict, target: dict):
        """target 하나를 조회한다. 반환: (status: str, train 또는 None)"""
        if not self.ensure_login():
            return "{}: 로그인 실패".format(STATUS_ERROR_PREFIX), None

        search_time = _time_minus_minutes(target["dep_time"], 5)
        try:
            trains = self._korail.search_train(
                group["dep"], group["arr"], group["date"], search_time,
                include_no_seats=True,
            )
        except NoResultsError:
            return STATUS_SOLDOUT, None
        except Exception as e:
            return "{}: {}".format(STATUS_ERROR_PREFIX, e), None

        for train in trains:
            if train.dep_time == target["dep_time"]:
                if train.has_seat():
                    return STATUS_AVAILABLE, train
                return STATUS_SOLDOUT, None

        # 목표 시각의 열차를 응답에서 찾지 못한 경우 (검색 범위를 벗어났을 가능성).
        # "매진"으로 잘못 표시하면 오해를 부르므로 별도 오류로 표시한다.
        return "{}: 해당 시각 열차를 응답에서 찾지 못함".format(STATUS_ERROR_PREFIX), None

    def reserve(self, train, adult_count: int = 1, seat_option: str = "GENERAL_FIRST"):
        option = getattr(ReserveOption, seat_option, ReserveOption.GENERAL_FIRST)
        passengers = [AdultPassenger(adult_count)]
        return self._korail.reserve(train, passengers, option=option)
