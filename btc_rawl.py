import csv
import time
from datetime import datetime, timedelta
from api.data_blockchain import fetch_klines


def fetch_2_years_h4(symbol="BTC"):
    """
    Fetch toàn bộ dữ liệu H4 trong 2 năm bằng cách gọi API nhiều lần
    """
    all_data = []

    # timestamp hiện tại
    to_timestamp = int(time.time())

    # timestamp 2 năm trước
    two_years_ago = datetime.now() - timedelta(days=3000)
    stop_timestamp = int(two_years_ago.timestamp())

    batch_limit = 2000  # max allowed

    while True:
        print(
            f"Fetching batch... toTs={datetime.fromtimestamp(to_timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        batch = fetch_klines(
            symbol=symbol,
            interval="1d",
            limit=batch_limit,
            to_timestamp=to_timestamp,
        )

        if not batch:
            break

        # prepend vào list
        all_data = batch + all_data

        # lấy timestamp candle đầu tiên để fetch tiếp lùi về trước
        first_timestamp = int(
            datetime.strptime(batch[0]["timestamp"], "%Y-%m-%d %H:%M:%S").timestamp()
        )

        # nếu đã tới 2 năm trước thì dừng
        if first_timestamp <= stop_timestamp:
            break

        # lùi thêm 1 giây để tránh trùng
        to_timestamp = first_timestamp - 1

        time.sleep(0.2)  # tránh rate limit

    print(f"Total fetched candles: {len(all_data)}")

    return all_data


def btc_daily():
    data = fetch_2_years_h4("BTC")

    print(f"fetch_klines: {len(data)} rows" if data else "empty")

    export_result_to_csv(data, "btc_data.csv")


def export_result_to_csv(result, filename="btc_data.csv"):
    if not result:
        print("Result empty")
        return

    fieldnames = list(result[0].keys())

    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result)

    print(f"Saved CSV: {filename}")


if __name__ == "__main__":
    btc_daily()
