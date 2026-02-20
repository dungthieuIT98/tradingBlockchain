import csv
from time import time
from api.data_blockchain import fetch_klines
from notify.notify import tele_notification
from strategy.ema_ribbon import add_ema_to_result
from strategy.ppo_pro import add_laguerre_ppo_percent_rank
from strategy.z_score_predict_zone import add_zscore_predictive_zones

DATA_CSV = "btc_data.csv"


def load_result_from_csv(filename):
    result = []
    try:
        with open(filename, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                converted_row = {}
                for key, value in row.items():
                    if value is None or value == "":
                        converted_row[key] = None
                    else:
                        try:
                            converted_row[key] = float(value)
                        except ValueError:
                            converted_row[key] = value
                result.append(converted_row)
        print(f"Loaded CSV: {filename} ({len(result)} rows)")
        return result
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return []
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []


def save_result_to_csv(result, filename):
    if not result:
        print("Result empty")
        return
    fieldnames = list(result[0].keys())
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in result:
            writer.writerow(row)
    print(f"Saved CSV: {filename}")


# def format_btc_message_all(data):
#     n = len(data)
#     for i in range(n):
#         latest = data[i]

#         timestamp = latest.get("timestamp") or latest.get("open_time") or "N/A"
#         trend = latest.get("ppo_pro_signal")
#         signal_zscore = latest.get("signal_zscore")

#         # Không có cả 2 thì không gửi
#         if not trend and not signal_zscore:
#             data[i]["message"] = None
#             # return None
#         else:
#             message = f"🕯 <b>BTC H4 </b>\n🕐 Time: <code>{timestamp}</code>\n"

#             if trend:
#                 message += f"📈 ppo_pro_signal: <b>{trend}</b>\n"

#             if signal_zscore:
#                 message += f"📊 Signal ZScore: <b>{signal_zscore}</b>"

#             print(message)
#             data[i]["message"] = message
#     return data


def format_btc_message(data):
    timestamp = data.get("timestamp") or data.get("open_time") or "N/A"
    trend = data.get("ppo_pro_signal")
    signal_zscore = data.get("signal_zscore")

    if not trend and not signal_zscore:
        print("⚠️ Không có signal, bỏ qua gửi Telegram.")
        return None

    message = f"🕯 <b>BTC H4 </b>\n🕐 Time: <code>{timestamp}</code>\n"

    if trend:
        message += f"📈 PPO Signal: <b>{trend}</b>\n"

    if signal_zscore:
        message += f"📊 Signal ZScore: <b>{signal_zscore}</b>"

    # print(message)

    return message


def process_btc_from_csv():
    # 1. Load data đã xử lý
    data = load_result_from_csv(DATA_CSV)
    if not data:
        print("Không có dữ liệu gốc, dừng lại.")
        return

    # 2. Fetch 1 record mới nhất
    new_record = fetch_klines(
        symbol="BTC",
        interval="1d",
        limit=1,
        to_timestamp=int(time()),
    )[-1]

    # 3. Kiểm tra trùng timestamp
    last_ts = data[-1].get("timestamp") or data[-1].get("open_time")
    new_ts = new_record.get("timestamp") or new_record.get("open_time")
    if str(last_ts) == str(new_ts):
        print(f"Record mới trùng timestamp ({new_ts}), bỏ qua.")
        return

    # 4. Append record mới
    data.append(new_record)

    # 5. Tính strategies
    # data = add_ema_to_result(data)
    data = add_zscore_predictive_zones(data)
    data = add_laguerre_ppo_percent_rank(data)

    # data = handle_signal(data)
    # format message cho tất cả records (nếu muốn)
    # data = format_btc_message_all(data)

    # 6. Ghi đè lại chính file đó
    save_result_to_csv(data, DATA_CSV)

    # 7. Gửi Telegram
    message = format_btc_message(data[-1])
    tele_notification(message)


if __name__ == "__main__":
    process_btc_from_csv()
