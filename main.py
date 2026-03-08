import os
# 【絕對關鍵】這行必須在最前面，解決你看到的 TypeError 錯誤
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. 基礎設定與 30 秒自動刷新
st.set_page_config(page_title="RICH CAT 戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="refresh")

# 2. 商品地圖
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "台積電 ADR": "TSM"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("請選擇商品", list(SYMBOL_MAP.keys()))
target_symbol = SYMBOL_MAP[selected_label]

# 3. 抓取數據 (加入防撞處理)
@st.cache_data(ttl=20)
def get_data(symbol):
    try:
        df = yf.download(symbol, period="10d", progress=False)
        # 處理多層標籤問題
        if df is not None and isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None

df = get_data(target_symbol)
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}")

# 4. 數據顯示
if df is not None and not df.empty:
    try:
        last = df.iloc[-1]
        def to_f(v): return float(v.iloc[0]) if isinstance(v, pd.Series) else float(v)
        c, h, l = to_f(last['Close']), to_f(last['High']), to_f(last['Low'])
        diff = h - l
        
        st.success(f"📈 {selected_label} 連線成功")
        col1, col2, col3 = st.columns(3)
        col1.metric("價格", f"{c:,.2f}")
        col2.metric("高點", f"{h:,.2f}")
        col3.metric("低點", f"{l:,.2f}")
        
        st.divider()
        st.info(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
        st.warning(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
    except:
        st.error("數據解析中...")
else:
    st.error("❌ 數據讀取中，請稍候。")
