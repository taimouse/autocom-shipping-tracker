"""일본 기준 영업일 판정 (주말/공휴일이면 스크래핑을 건너뛴다).

GitHub Actions에서 실행하면 GITHUB_OUTPUT 에 should_run=true|false 를 기록하고,
이후 스텝들이 이 값으로 실행 여부를 결정한다.
수동 실행(workflow_dispatch)은 휴일이라도 항상 실행되도록 통과시킨다.

로컬에서 단독 실행하면 영업일이면 종료 코드 0, 휴일이면 1을 반환한다.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import jpholiday

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=9))
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def skip_reason(day):
    """건너뛰어야 하면 사유 문자열, 영업일이면 None."""
    if day.weekday() >= 5:
        return f"주말({WEEKDAY_KR[day.weekday()]}요일)"
    name = jpholiday.is_holiday_name(day)
    if name:
        return f"공휴일({name})"
    return None


def main():
    today = datetime.now(JST).date()

    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        reason = None
        print(f"[{today} JST] 수동 실행 - 휴일 검사를 건너뛰고 스크래핑을 진행합니다")
    else:
        reason = skip_reason(today)
        if reason:
            print(f"[{today} JST] {reason} - 스크래핑을 건너뜁니다")
        else:
            print(f"[{today} JST] 일본 영업일 - 스크래핑을 진행합니다")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"should_run={'false' if reason else 'true'}\n")
        return 0

    return 1 if reason else 0


if __name__ == "__main__":
    sys.exit(main())
