import streamlit as st
import requests
import time
import os
import pandas as pd
from datetime import datetime, timedelta

import json

# ================= 配置区域 =================
STOCK_A_CODE = "sh600036"
STOCK_A_NAME = "招商银行"

STOCK_B_CODE = "sz002142"
STOCK_B_NAME = "宁波银行"

REFRESH_RATE = 3       # 刷新间隔 (秒)
ALERT_COOLDOWN = 300   # 报警冷却时间 (秒)
CONFIG_FILE = "monitor_config.json" # 配置文件路径
# ===========================================

# 设置页面标题和布局
st.set_page_config(page_title="配对交易监控", page_icon="📈", layout="centered")

# --- 初始化 Session State ---
if 'last_alert_time' not in st.session_state:
    st.session_state.last_alert_time = 0

# --- 配置文件管理 ---
def load_config():
    default_config = {
        "ratio_mean": 1.330,
        "ratio_std": 0.015,
        "z_threshold": 2.4
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**default_config, **json.load(f)}
        except:
            pass
    return default_config

def save_config():
    config = {
        "ratio_mean": st.session_state.ratio_mean,
        "ratio_std": st.session_state.ratio_std,
        "z_threshold": st.session_state.z_threshold
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except Exception as e:
        st.error(f"保存配置失败: {e}")

# --- 通知功能 ---
def load_secrets():
    # 优先从 Streamlit Secrets 读取，其次环境变量
    bark = st.secrets.get("BARK_KEY") if "BARK_KEY" in st.secrets else os.environ.get("BARK_KEY")
    pp = st.secrets.get("PUSHPLUS_TOKEN") if "PUSHPLUS_TOKEN" in st.secrets else os.environ.get("PUSHPLUS_TOKEN")
    return bark, pp

def send_notification(title, content):
    bark_key, pp_token = load_secrets()
    
    # 1. Bark 推送
    if bark_key:
        try:
            base_url = bark_key if bark_key.startswith("http") else f"https://api.day.app/{bark_key}/"
            clean_url = base_url.rstrip('/')
            # URL Encode 可能需要，这里简单处理
            requests.get(f"{clean_url}/{title}/{content}?group=stock_monitor", timeout=5)
        except Exception as e:
            st.error(f"Bark 推送失败: {e}")

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
            requests.post(pp_url, json=pp_data, timeout=5)
        except Exception as e:
            st.error(f"PushPlus 推送失败: {e}")

# 定义获取数据的函数
def get_realtime_data():
    url = f"http://hq.sinajs.cn/list={STOCK_A_CODE},{STOCK_B_CODE}"
    headers = {'Referer': 'http://finance.sina.com.cn'}
    try:
        resp = requests.get(url, headers=headers, timeout=2)
        if resp.status_code != 200: return None

        lines = resp.text.split('\n')
        data = {}

        # 解析数据
        for i, code in enumerate(['A', 'B']):
            line = lines[i]
            if '="' in line:
                elements = line.split('=')[1].strip('";').split(',')
                if len(elements) > 30:
                    current = float(elements[3])
                    data[code] = {'price': current}
        return data
    except:
        return None

# --- 侧边栏配置 ---
config = load_config() # 加载配置

with st.sidebar:
    st.header("⚙️ 监控设置")
    
    st.subheader("📊 历史统计参数")
    # 使用 key 和 on_change 实现双向绑定和持久化
    ratio_mean = st.number_input(
        "Ratio 40日均值 (Mean)", 
        value=config["ratio_mean"], 
        step=0.001, 
        format="%.3f",
        key="ratio_mean",
        on_change=save_config
    )
    ratio_std = st.number_input(
        "Ratio 40日标准差 (Std)", 
        value=config["ratio_std"], 
        step=0.001, 
        format="%.3f",
        key="ratio_std",
        on_change=save_config
    )
    
    st.subheader("⚡ 交易触发参数")
    z_threshold = st.slider(
        "开仓阈值 (倍标准差)", 
        1.5, 3.0, 
        config["z_threshold"], 
        0.1,
        key="z_threshold",
        on_change=save_config
    )
    
    auto_refresh = st.checkbox("开启自动刷新", value=True)
    st.info("数据来源：新浪财经 (延迟约3秒)")
    st.caption(f"报警冷却: {ALERT_COOLDOWN}秒")

# --- 辅助函数 ---
def is_trading_time(dt):
    """
    判断是否在A股交易时间
    上午: 09:30 - 11:30
    下午: 13:00 - 15:00
    """
    # 周末不交易
    if dt.weekday() >= 5: return False
    
    current_time = dt.time()
    morning_start = datetime.strptime("09:30", "%H:%M").time()
    morning_end = datetime.strptime("11:30", "%H:%M").time()
    afternoon_start = datetime.strptime("13:00", "%H:%M").time()
    afternoon_end = datetime.strptime("15:00", "%H:%M").time()

    return (morning_start <= current_time <= morning_end) or \
           (afternoon_start <= current_time <= afternoon_end)

# --- 主界面 ---
st.title("📈 银行股配对监控 (Z-Score)")

# 创建占位符容器，用于动态更新内容
main_container = st.empty()

while True:
    # 获取北京时间 (云服务器通常是UTC，需要+8小时)
    now_dt = datetime.utcnow() + timedelta(hours=8)
    now_time_str = now_dt.strftime("%H:%M:%S")

    # 交易时间检查
    if is_trading_time(now_dt):
        status_text = f"最后更新时间: {now_time_str}"
        data = get_realtime_data()
    else:
        status_text = f"最后更新时间: {now_time_str} (😴 休息中)"
        data = None

    with main_container.container():
        # 1. 顶部状态栏
        st.caption(status_text)

        if data and 'A' in data and 'B' in data:
            price_a = data['A']['price']
            price_b = data['B']['price']
            
            # 【新增】防除零崩溃机制
            if price_b <= 0 or price_a <= 0:
                st.error("⚠️ 获取到异常价格 (为0)，可能接口故障或停牌，暂停本次计算！")
                time.sleep(REFRESH_RATE)
                continue

            # 核心计算
            current_ratio = price_a / price_b
            z_score = (current_ratio - ratio_mean) / ratio_std
            
            # Data validation to prevent division by zero or errors
            if ratio_std == 0:
                z_score = 0
                st.error("标准差不能为0，请检查侧边栏设置！")

            # 2. 核心指标卡片 (三列布局)
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    label=STOCK_A_NAME,
                    value=f"¥{price_a:.2f}",
                )

            with col2:
                # Ratio / Z-Score 卡片
                st.metric(
                    label="当前比价 Ratio (A/B)",
                    value=f"{current_ratio:.4f}",
                    delta=f"Z: {z_score:.2f}σ"
                )

            with col3:
                st.metric(
                    label=STOCK_B_NAME,
                    value=f"¥{price_b:.2f}",
                )

            # 3. 信号判定逻辑
            st.divider()
            
            abs_z = abs(z_score)
            
            # --- 级别 A: 熔断防爆死 ---
            if abs_z > 3.5:
                alert_msg = f"⛔ 熔断报警：出现极端异常 (Z-Score: {z_score:.2f})！请立刻停止任何开仓，检查基本面！"
                st.error(alert_msg)
                
                # 熔断也必须推送！
                current_timestamp = time.time()
                if current_timestamp - st.session_state.last_alert_time > ALERT_COOLDOWN:
                    send_notification("🚨 紧急熔断报警", alert_msg)
                    st.session_state.last_alert_time = current_timestamp
            
            # --- 级别 B: 开仓信号 ---
            elif abs_z > z_threshold:
                alert_msg = ""
                # 如果 Z-Score > 阈值，说明 Ratio 只有过高，A 贵 B 便宜 -> 卖 A 买 B
                if z_score > 0:
                    alert_msg = f"🔴 卖强买弱信号触发：卖出{STOCK_A_NAME}，买入{STOCK_B_NAME} (Z: {z_score:.2f} > {z_threshold})"
                    st.error(alert_msg)
                # 如果 Z-Score < -阈值，说明 Ratio 过低，A 便宜 B 贵 -> 买 A 卖 B
                else:
                    alert_msg = f"🟢 卖弱买强信号触发：卖出{STOCK_B_NAME}，买入{STOCK_A_NAME} (Z: {z_score:.2f} < -{z_threshold})"
                    st.error(alert_msg)
                
                # --- 推送逻辑 ---
                current_timestamp = time.time()
                if current_timestamp - st.session_state.last_alert_time > ALERT_COOLDOWN:
                    send_notification("配对交易信号触发", alert_msg)
                    st.session_state.last_alert_time = current_timestamp
                    st.toast("🚀 已触发自动推送", icon="✅")
                else:
                    remaining = int(ALERT_COOLDOWN - (current_timestamp - st.session_state.last_alert_time))
                    st.caption(f"🔔 报警冷却中，剩余 {remaining} 秒")
            
            # --- 级别 C: 平仓区域 ---
            elif abs_z < 0.2:
                st.success(f"✅ 均值回归：当前比价已回归正常范围 (Z: {z_score:.2f})，若是持仓中可考虑获利平仓。")
            
            # --- 级别 D: 正常观望 ---
            else:
                 st.info(f"⚓ 波动正常，持仓观望 (Z: {z_score:.2f})。")

            # 4. 图表优化：Z-Score 仪表盘
            # 创建一个简单的 DataFrame用于展示 Z-Score 相对于阈值的位置
            # 这里的可视化使用简单的 progress chart 或者 metric 可能会比较抽象，
            # 使用 altair 或者简单的 st.progress 可能更好，但 st.progress 只能 0-100。
            # 这里我们用一个水平的 bar chart 来模拟 0 轴在中间的效果，或者直接用 metric。
            # 为了直观，我们还是用 bar_chart，但是构造数据让它围绕 0 上下波动
            
            chart_df = pd.DataFrame({
                'Index': ['Z-Score'],
                'Value': [z_score]
            })
            
            # 添加阈值辅助线 (通过 hack 图表或者简单展示)
            # 由于 Streamlit 原生 chart 简单，我们直接画一个值
            st.write("##### Z-Score 偏离度监控")
            st.bar_chart(chart_df.set_index('Index'), color="#FF4B4B" if abs_z > z_threshold else "#4BFF4B")
            
            st.caption(f"开仓阈值区间: [-{z_threshold}, +{z_threshold}]")

        elif not is_trading_time(now_dt):
            st.info("😴 当前非交易时间，暂停数据更新")
        else:
            st.warning("正在连接行情数据...")

    # 如果未开启自动刷新，则跳出循环
    if not auto_refresh:
        break

    # 休市期间休眠更久 (60秒)，交易时间正常刷新
    sleep_time = 60 if not is_trading_time(now_dt) else REFRESH_RATE
    time.sleep(sleep_time)
