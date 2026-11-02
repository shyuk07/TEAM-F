"""auth-security-check 스크립트 공통 도우미: src/ 경로 설정과 결과 집계."""
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src"


def use_src() -> None:
    """어디서 실행하든 src/를 import 기준 경로로 쓴다 (uvicorn --app-dir src와 같음)."""
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    os.chdir(SRC)
    # passlib 1.7.4가 bcrypt 4.x 버전을 읽지 못해 남기는 "(trapped) error reading bcrypt version" 로그를 숨긴다 (동작에는 영향 없음).
    logging.getLogger("passlib").setLevel(logging.ERROR)


class Report:
    """항목별 결과를 통과 / 위반 / 해당없음 / 주의로 출력하고, 위반이 있으면 종료코드 1."""

    def __init__(self, title: str):
        self.title = title
        self.counts = {"통과": 0, "위반": 0, "해당없음": 0, "주의": 0}
        print(f"== {title}")

    def section(self, title: str) -> None:
        print(f"\n== {title}")

    def add(self, status: str, name: str, detail: str = "") -> None:
        self.counts[status] += 1
        print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))

    def check(self, ok: bool, name: str, detail: str = "") -> bool:
        self.add("통과" if ok else "위반", name, detail)
        return ok

    def finish(self) -> None:
        summary = ", ".join(f"{k} {v}" for k, v in self.counts.items())
        print(f"-- {self.title} 결과: {summary}")
        sys.exit(1 if self.counts["위반"] else 0)
