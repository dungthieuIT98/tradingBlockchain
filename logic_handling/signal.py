def handle_signal(result):
    for item in result:
        # đảm bảo item là dict
        if not isinstance(item, dict):
            continue

        # tạo cột notify mặc định
        item["notify"] = None

        if item.get("long_signal"):
            item["notify"] = "long signal"

        elif item.get("short_signal"):
            item["notify"] = "short signal"

    return result
