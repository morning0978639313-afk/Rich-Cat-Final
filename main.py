import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心設定：30秒自動刷新
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="強哥戰技戰情室", layout="wide")
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 指定商品清單 (FinMind 格式)
SYMBOL_MAP = {
    "加權指數": "TAIWAN_STOCK_INDEX",
    "微台近全": "MTX", # 微台指
    "台積電": "2330",
    "00850 (ESG永續)": "00850",
    "0052 (科技)": "0052"
}

st.title("🐱 RICH CAT 實戰戰情室")
selected_label = st.selectbox("🎯 選擇監控商品", list(SYMBOL_MAP.keys()))

# 2. 獲取精準數據 (FinMind 通道)
@st.cache_data(ttl=30)
def get_battle_data(stock_id):
    try:
        dl = DataLoader()
        # 抓取最近 10 天數據
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        if stock_id == "TAIWAN_STOCK_INDEX":
            df = dl.taiwan_stock_index_daily(stock_id=stock_id, start_date=start_date)
        else:
            df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
            
        if df is not None and not df.empty:
            df = df.rename(columns={'close': 'Close', 'high': 'High', 'low': 'Low', 'open': 'Open', 'date': 'Date'})
            return df
        return None
    except:
        return None

df = get_battle_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
now_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"🕒 台北實時：`{now_str}`")

# 3. RICH CAT 戰技邏輯實作
if df is not None and not df.empty:
    last = df.iloc[-1]
    # 今日數據
    c, h, l, o = float(last['Close']), float(last['High']), float(last['Low']), float(last['Open'])
    diff = h - l
    
    # --- 戰技一：開盤價多空生命線 ---
    if c >= o:
        st.success(f"🔥 強勢力道：目前價格 ({c:,.2f}) 位於今日開盤價 ({o:,.2f}) 之上")
    else:
        st.warning(f"❄️ 弱勢力道：目前價格 ({c:,.2f}) 位於今日開盤價 ({o:,.2f}) 之下")

    # 數據看板
    col1, col2, col3 = st.columns(3)
    col1.metric("當前點位", f"{c:,.2f}")
    col2.metric("當日最高", f"{h:,.2f}")
    col3.metric("當日最低", f"{l:,.2f}")

    st.markdown("---")

    # --- 戰技二：黃金切割率 (單元三) ---
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    col_p, col_s = st.columns(2)
    with col_p:
        st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    with col_s:
        st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")

    # --- 戰術三：主力攻擊密碼 (紅黑三兵) ---
    if len(df) >= 3:
        last_3 = df.tail(3)
        # 紅三兵
        if all(last_3['Close'] > last_3['Open']):
            st.error("🚨 【紅三兵】主力多方連續攻擊訊號！")
        # 黑三兵
        elif all(last_3['Close'] < last_3['Open']):
            st.error("🚨 【黑三兵】主力空方連續壓制訊號！")

    # 顯示圖表
    st.line_chart(df.set_index('Date')['Close'])
else:
    st.error("❌ 通道連線中...請稍候 30 秒或點擊左側 Manage app 重啟 (Reboot)。")
