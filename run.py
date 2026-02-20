import time

from btc import process_btc_from_csv

if __name__ == "__main__":
    import os

    while True:
        try:
            process_btc_from_csv()
        except Exception as e:
            print(f"Lỗi: {e}")
            time.sleep(60)
