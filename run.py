from datetime import datetime, timezone, timedelta
import time

from btc import process_btc_from_csv


def wait_until_7am():
    now = datetime.now(timezone.utc)
    target = now.replace(hour=7, minute=0, second=10, microsecond=0)

    # Nếu đã qua 7h hôm nay thì chờ đến 7h ngày mai
    if now >= target:
        target += timedelta(days=1)

    wait_seconds = (target - now).total_seconds()
    print(f"Chờ {wait_seconds/3600:.2f}h → 7h sáng UTC lúc {target} UTC")
    time.sleep(wait_seconds)


if __name__ == "__main__":
    import os

    while True:
        try:
            wait_until_7am()
            process_btc_from_csv()
        except Exception as e:
            print(f"Lỗi: {e}")
            time.sleep(60)
