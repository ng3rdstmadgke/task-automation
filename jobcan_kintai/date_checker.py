#!/usr/bin/env python3
"""
土日・祝日・有給日を判定するモジュール
"""
import json
from datetime import datetime
from pathlib import Path
import jpholiday


def load_paid_leave_days(config_path: str = "config.json") -> list[str]:
    """config.jsonから有給日リストを読み込む"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("paid_leave_days", [])
    except FileNotFoundError:
        print(f"警告: {config_path} が見つかりません。有給日なしとして処理します")
        return []
    except json.JSONDecodeError as e:
        print(f"エラー: {config_path} のJSONパースに失敗しました - {e}")
        raise


def is_weekend(target_date: datetime) -> bool:
    """土日かどうかを判定"""
    return target_date.weekday() in (5, 6)


def is_holiday(target_date: datetime) -> bool:
    """祝日かどうかを判定"""
    return jpholiday.is_holiday(target_date)


def is_paid_leave(target_date: datetime, paid_leave_days: list[str]) -> bool:
    """有給日かどうかを判定"""
    target_str = f"{target_date.month}/{target_date.day}"
    return target_str in paid_leave_days


def should_skip_punch(target_date: datetime, config_path: str = "config.json") -> tuple[bool, str]:
    """打刻をスキップすべきかどうかを判定"""
    if is_weekend(target_date):
        weekday_name = "土曜日" if target_date.weekday() == 5 else "日曜日"
        return True, f"{weekday_name}のため"

    if is_holiday(target_date):
        holiday_name = jpholiday.is_holiday_name(target_date)
        return True, f"祝日（{holiday_name}）のため"

    paid_leave_days = load_paid_leave_days(config_path)
    if is_paid_leave(target_date, paid_leave_days):
        return True, "有給休暇のため"

    return False, ""


if __name__ == "__main__":
    today = datetime.now()
    should_skip, reason = should_skip_punch(today)

    print(f"日付: {today.strftime('%Y年%m月%d日')}")
    if should_skip:
        print(f"判定: スキップ（{reason}）")
    else:
        print("判定: 打刻実行")
