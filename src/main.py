# -*- coding: utf-8 -*-
"""
코레일 취소표 예매 보조 도구 - 데스크톱 GUI

핵심 원칙: 이 프로그램은 스스로 반복 실행되지 않는다.
"② 지금 1회 확인하기" 버튼을 누를 때만 딱 한 번 조회한다 (자동 반복 없음).
결제는 절대 자동으로 하지 않는다 - 좌석을 임시 예약(선택)까지만 하고 알림을 보낸다.
"""
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

import login_manager
import state_store
from korail_client import KorailClient, STATUS_AVAILABLE
from telegram_notifier import TelegramNotifier

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("코레일 취소표 예매 보조 도구")

        load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
        self.config = load_config()
        self.notifier = TelegramNotifier()
        self.client = None
        self.row_widgets = {}  # target_id -> status_label

        self._build_ui()
        self._render_targets()

    # ---------- UI 구성 ----------
    def _build_ui(self):
        top = tk.Frame(self.root, padx=10, pady=10)
        top.pack(fill="x")

        tk.Button(
            top, text="① 로그인 확인 / 조건 불러오기", width=28,
            command=self.on_click_prepare,
        ).pack(side="left", padx=4)
        tk.Button(
            top, text="② 지금 1회 확인하기", width=20,
            command=self.on_click_check_once,
        ).pack(side="left", padx=4)

        self.status_frame = tk.Frame(self.root, padx=10, pady=5)
        self.status_frame.pack(fill="x")

        log_frame = tk.Frame(self.root, padx=10, pady=10)
        log_frame.pack(fill="both", expand=True)
        tk.Label(log_frame, text="로그").pack(anchor="w")
        self.log_box = scrolledtext.ScrolledText(log_frame, height=14, state="disabled")
        self.log_box.pack(fill="both", expand=True)

        if not self.notifier.is_configured():
            self._log("[경고] 텔레그램 알림이 설정되지 않았습니다. .env 파일(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)을 확인하세요.")

    def _render_targets(self):
        for widget in self.status_frame.winfo_children():
            widget.destroy()
        self.row_widgets.clear()

        secured = state_store.load_secured()
        row = 0
        for group in self.config["search_groups"]:
            for target in group["targets"]:
                target_id = self._target_id(group, target)
                is_secured = target_id in secured
                status_text = "확보완료" if is_secured else "대기중"

                tk.Label(self.status_frame, text=target["label"], width=30, anchor="w").grid(
                    row=row, column=0, sticky="w", pady=1
                )
                status_label = tk.Label(self.status_frame, text=status_text, width=20, anchor="w")
                status_label.grid(row=row, column=1, sticky="w")

                self.row_widgets[target_id] = status_label
                row += 1

    @staticmethod
    def _target_id(group: dict, target: dict) -> str:
        return "{}::{}".format(group["id"], target["dep_time"])

    def _log(self, message: str):
        def _append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.root.after(0, _append)

    def _set_status(self, target_id: str, text: str):
        def _update():
            if target_id in self.row_widgets:
                self.row_widgets[target_id].config(text=text)

        self.root.after(0, _update)

    # ---------- 버튼 ① : 로그인 확인 / 조건 불러오기 ----------
    def on_click_prepare(self):
        korail_id, korail_pw = login_manager.load_credentials()
        if not korail_id or not korail_pw:
            korail_id = simpledialog.askstring("코레일 로그인", "코레일 회원번호/이메일/전화번호:")
            korail_pw = simpledialog.askstring("코레일 로그인", "비밀번호:", show="*")
            if not korail_id or not korail_pw:
                messagebox.showwarning("입력 필요", "로그인 정보를 입력해야 합니다.")
                return
            login_manager.save_credentials(korail_id, korail_pw)
            self._log("[정보] 로그인 정보를 암호화하여 저장했습니다 (Windows 자격 증명 관리자 이용).")

        self.client = KorailClient(korail_id, korail_pw)
        self._log("[정보] 코레일 로그인 확인 중...")

        def worker():
            ok = self.client.ensure_login()
            if ok:
                self._log("[성공] 코레일 로그인 확인 완료.")
            else:
                self._log("[실패] 코레일 로그인 실패. 아이디/비밀번호를 확인하세요.")

        threading.Thread(target=worker, daemon=True).start()
        self._render_targets()

    # ---------- 버튼 ② : 지금 1회 확인하기 ----------
    def on_click_check_once(self):
        if self.client is None:
            messagebox.showinfo("안내", "먼저 '① 로그인 확인 / 조건 불러오기'를 눌러주세요.")
            return
        threading.Thread(target=self._check_once_worker, daemon=True).start()

    def _check_once_worker(self):
        self._log("---- 1회 확인 시작 ----")
        secured = state_store.load_secured()
        adult_count = self.config.get("adult_count", 1)
        seat_option = self.config.get("seat_option", "GENERAL_FIRST")

        for group in self.config["search_groups"]:
            for target in group["targets"]:
                target_id = self._target_id(group, target)
                if target_id in secured:
                    continue

                status, train = self.client.check_target(group, target)
                self._set_status(target_id, status)
                self._log("{} -> {}".format(target["label"], status))

                if status == STATUS_AVAILABLE and train is not None:
                    self._handle_seat_found(target_id, target, train, adult_count, seat_option)

        self._log("---- 1회 확인 종료 ----")

    def _handle_seat_found(self, target_id, target, train, adult_count, seat_option):
        try:
            reservation = self.client.reserve(train, adult_count, seat_option)
        except Exception as e:
            self._log("[예약 실패] {}: {}".format(target["label"], e))
            return

        state_store.mark_secured(target_id)
        self._set_status(target_id, "확보완료(결제 필요)")
        self._log(
            "[예약 성공] {} - 결제기한: {} {}".format(
                target["label"],
                getattr(reservation, "buy_limit_date", "?"),
                getattr(reservation, "buy_limit_time", "?"),
            )
        )

        message = (
            "\U0001F684 좌석 발생! 임시 예약 완료\n"
            "{}\n"
            "코레일 사이트/앱에서 빨리 결제해주세요 (제한시간 있음)."
        ).format(target["label"])
        sent = self.notifier.send(message)
        if not sent:
            self._log("[경고] 텔레그램 알림 전송 실패! 지금 바로 직접 코레일 앱/사이트를 확인하세요.")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
