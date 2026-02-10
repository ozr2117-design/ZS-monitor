import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, timedelta

# ================= 配置区域 =================
STOCK_A_CODE = "sh600036"
STOCK_A_NAME = "招商银行"

STOCK_B_CODE = "sz002142"
STOCK_B_NAME = "宁波银行"

SPREAD_THRESHOLD = 1.0 # 报警阈值 1%
REFRESH_RATE = 3       # 刷新间隔 (秒)
# ===========================================

# 设置页面标题和布局
st.set_page_config(page_title="配对交易监控", page_icon="📈", layout="centered")

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
                    pre_close = float(elements[2])
                    pct = (current - pre_close) / pre_close * 100
                    data[code] = {'price': current, 'pct': pct}
        return data
    except:
        return None

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 监控设置")
    threshold = st.slider("报警阈值 (%)", 0.5, 3.0, 1.0, 0.1)
    auto_refresh = st.checkbox("开启自动刷新", value=True)
    st.info("数据来源：新浪财经 (延迟约3秒)")

# --- 主界面 ---
st.title("📈 银行股配对监控")

# 创建占位符容器，用于动态更新内容
main_container = st.empty()

while True:
    # 获取北京时间 (云服务器通常是UTC，需要+8小时)
    now_time = (datetime.utcnow() + timedelta(hours=8)).strftime("%H:%M:%S")

    data = get_realtime_data()

    with main_container.container():
        if data and 'A' in data and 'B' in data:
            spread = data['A']['pct'] - data['B']['pct']

            # 1. 顶部状态栏
            st.caption(f"最后更新时间: {now_time}")

            # 2. 核心指标卡片 (三列布局)
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    label=STOCK_A_NAME,
                    value=f"¥{data['A']['price']:.2f}",
                    delta=f"{data['A']['pct']:.2f}%"
                )

            with col2:
                # 价差卡片
                # 使用自定义逻辑判断颜色，因此这里delta_color设为off
                st.metric(
                    label="当前价差 (A-B)",
                    value=f"{spread:+.2f}%",
                    delta_color="off"
                )

            with col3:
                st.metric(
                    label=STOCK_B_NAME,
                    value=f"¥{data['B']['price']:.2f}",
                    delta=f"{data['B']['pct']:.2f}%"
                )

            # 3. 报警逻辑
            st.divider()

            # 使用侧边栏设置的动态阈值
            if abs(spread) >= threshold:
                # 触发报警：显示醒目的红色警告框
                if spread > 0:
                    st.error(f"🔥🔥 信号触发！卖出【{STOCK_A_NAME}】，买入【{STOCK_B_NAME}】")
                    st.markdown(f"**当前价差 {spread:.2f}% > 阈值 {threshold}%**")
                else:
                    st.error(f"🔥🔥 信号触发！卖出【{STOCK_B_NAME}】，买入【{STOCK_A_NAME}】")
                    st.markdown(f"**当前价差 {abs(spread):.2f}% > 阈值 {threshold}%**")

            else:
                # 正常状态
                st.success(f"✅ 波动正常，安心持股 (当前价差 < 阈值 {threshold}%)")

                # 显示一个简单的柱状图辅助观察
                chart_data = pd.DataFrame({
                    '股票名称': [STOCK_A_NAME, STOCK_B_NAME],
                    '今日涨跌幅(%)': [data['A']['pct'], data['B']['pct']]
                })
                st.bar_chart(chart_data.set_index('股票名称'))

        else:
            st.warning("正在连接行情数据...")

    # 如果未开启自动刷新，则跳出循环
    if not auto_refresh:
        break

    # 暂停等待下一次刷新
    time.sleep(REFRESH_RATE)
