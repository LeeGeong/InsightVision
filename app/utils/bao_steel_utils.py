import os
from datetime import datetime

import pandas as pd


def update_stats_to_csv(status: str, csv_path: str = "static/ocr_stats.csv"):
    """
    更新每日统计到 CSV 文件。

    Args:
        status (str): "success" 或 "failure"
        csv_path (str): CSV 文件保存路径
    """
    today = datetime.today().strftime('%Y-%m-%d')
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    new_row = {"date": today, "success": 0, "failure": 0}
    if status == "success":
        new_row["success"] = 1
    else:
        new_row["failure"] = 1

    if not os.path.exists(csv_path):
        df = pd.DataFrame([new_row])
    else:
        try:
            df = pd.read_csv(csv_path)

            if df.empty:
                df = pd.DataFrame([new_row])
            else:
                df["date"] = pd.to_datetime(df["date"]).dt.strftime('%Y-%m-%d')
                last_date = df.iloc[-1]["date"]

                if last_date == today:
                    if status == "success":
                        df.at[df.index[-1], "success"] += 1
                    else:
                        df.at[df.index[-1], "failure"] += 1
                else:
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        except Exception as e:
            print(f"读取 CSV 失败，重新创建文件: {e}")
            df = pd.DataFrame([new_row])

    df["success"] = df["success"].astype(int)
    df["failure"] = df["failure"].astype(int)

    try:
        df.to_csv(csv_path, index=False)
    except Exception as e:
        print(f"写入 CSV 失败: {e}")
        raise

    today_stats = df[df["date"] == today].iloc[0]
    return {
        "daily_success": int(today_stats["success"]),
        "daily_failure": int(today_stats["failure"])
    }
