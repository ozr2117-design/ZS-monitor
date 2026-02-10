import requests
import os
import time
from datetime import datetime, timedelta

# ================= 配置区域 =================
STOCK_A_CODE = "sh600036"
STOCK_A_NAME = "招商银行"

STOCK_B_CODE = "sz002142"
STOCK_B_NAME = "宁波银行"

SPREAD_THRESHOLD = 1.0 # 报警阈值 1%
# ===========================================

def load_secrets():
    bark = os.environ.get("BARK_KEY")
    pp = os.environ.get("PUSHPLUS_TOKEN")
    return bark, pp

def send_notification(title, content):
    bark_key, pp_token = load_secrets()
    print(f"Sending notification: {title} - {content}")
    
    # 1. Bark 推送
    if bark_key:
        try:
            base_url = bark_key if bark_key.startswith("http") else f"https://api.day.app/{bark_key}/"
            clean_url = base_url.rstrip('/')
            requests.get(f"{clean_url}/{title}/{content}?group=stock_monitor", timeout=10)
        except Exception as e:
            print(f"Bark Error: {e}")

    # 2. PushPlus 推送
    if pp_token:
        try:
            pp_url = "http://www.pushplus.plus/send"
            pp_data = {
                "token": pp_token,
                "title": title,
                "content": content.replace("\n", "<br>"), 
                "template": "html"
            }
            requests.post(pp_url, json=pp_data, timeout=10)
        except Exception as e:
            print(f"PushPlus Error: {e}")

def get_realtime_data():
    url = f"http://hq.sinajs.cn/list={STOCK_A_CODE},{STOCK_B_CODE}"
    headers = {'Referer': 'http://finance.sina.com.cn'}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200: return None

        lines = resp.text.split('\n')
        data = {}

        for i, code in enumerate(['A', 'B']):
            line = lines[i]
            if '="' in line:
                elements = line.split('=')[1].strip('";').split(',')
                if len(elements) > 30:
                    current = float(elements[3])
                    pre_close = float(elements[2])
                    pct = (current - pre_close) / pre_close * 100
                    data[code] = {'price': current, 'pct': pct}
        return data
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return None

def is_trading_time(dt):
    if dt.weekday() >= 5: return False
    current_time = dt.time()
    return (datetime.strptime("09:30", "%H:%M").time() <= current_time <= datetime.strptime("11:30", "%H:%M").time()) or \
           (datetime.strptime("13:00", "%H:%M").time() <= current_time <= datetime.strptime("15:00", "%H:%M").time())

def main():
    print("Starting check...")
    # 获取北京时间
    utc_now = datetime.utcnow()
    bj_now = utc_now + timedelta(hours=8)
    
    # 交易时间过滤 (9:30 - 11:30, 13:00 - 15:00)
    print(f"Time (BJ): {bj_now}")
    
    if not is_trading_time(bj_now):
        print("Market Closed. Spending time detecting if I should sleep...")
        return

    data = get_realtime_data()
    if data and 'A' in data and 'B' in data:
        spread = data['A']['pct'] - data['B']['pct']
        print(f"Spread: {spread:.2f}%")

        if abs(spread) >= SPREAD_THRESHOLD:
            msg = ""
            if spread > 0:
                msg = f"卖出【{STOCK_A_NAME}】，买入【{STOCK_B_NAME}】\n价差 {spread:.2f}% > {SPREAD_THRESHOLD}%"
            else:
                msg = f"卖出【{STOCK_B_NAME}】，买入【{STOCK_A_NAME}】\n价差 {abs(spread):.2f}% > {SPREAD_THRESHOLD}%"
            
            print("!!! TRIGGER !!!")
            send_notification("配对交易信号触发", msg)
        else:
            print("No signal.")
    else:
        print("Failed to get data.")

if __name__ == "__main__":
    main()
