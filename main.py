import os
import subprocess
import sys

# 1. 核心環境校正：解決伺服器端 Protobuf 衝突
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 2. 戰情室基礎設定
st.set_page_config(
    page_title="RICH CAT 終極戰情室", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 每 30 秒自動刷新，確保點位即時
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 3. 標的清單
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "台積電 ADR": "TSM",
    "ESG 永續 (00850)": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

@st.cache_data(ttl=20)
def get_data(symbol):
    try:
        # 下載最近 10 天數據
        df = yf.download(symbol, period="10d", interval="1d", progress=False)
        if df is not None and not df.empty:
            # 處理 yfinance 的 MultiIndex 欄位問題
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        return None
    except Exception as e:
        return None

# 獲取資料
df = get_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

st.write(f"🕒 台北實時：`{current_time}`")

# 4. 點位計算與顯示邏輯
if df is not None and not df.empty:
    last = df.iloc[-1]
    
    # 數值轉換保護
    def to_f(v): 
        try:
            return float(v.iloc[0]) if hasattr(v, 'iloc') else float(v)
        except:
            return float(v)
    
    c = to_f(last['Close'])
    h = to_f(last['High'])
    l = to_f(last['Low'])
    diff = h - l
    
    st.success(f"✅ {selected_label} 連線成功")
    
    # 指標看板
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價", f"{c:,.2f}")
    col2.metric("最高", f"{h:,.2f}")
    col3.metric("最低", f"{l:,.2f}")
    
    st.divider()
    
    # 戰技點位計算
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")
    
    # 趨勢圖表 (使用內建簡單圖表避免 Altair 相容性問題)
    st.subheader("📊 近期走勢 (收盤價)")
    st.line_chart(df['Close'])

else:
    st.error("❌ 伺服器忙碌中，請點擊 Manage app 執行 Reboot。")
