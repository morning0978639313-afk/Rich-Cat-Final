import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 基礎設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=60 * 1000, key="datarefresh") # FinMind 建議 60 秒刷一次

# 轉換 yfinance 代碼為 FinMind 格式
SYMBOL_MAP = {
    "加權指數": "TAIWAN_STOCK_INDEX",
    "台積電": "2330",
    "00850": "00850"
}

st.title("🐱 RICH CAT 終極戰情室 (穩定版)")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

@st.cache_data(ttl=60)
def get_finmind_data(symbol):
    try:
        dl = DataLoader()
        # 抓取最近 15 天的資料
        start_date = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        
        if symbol == "TAIWAN_STOCK_INDEX":
            df = dl.taiwan_stock_index_daily(stock_id="TAIWAN_STOCK_INDEX", start_date=start_date)
        else:
            df = dl.taiwan_stock_daily(stock_id=symbol, start_date=start_date)
            
        if df is not None and not df.empty:
            df = df.rename(columns={'close': 'Close', 'high': 'High', 'low': 'Low', 'date': 'Date'})
            return df
        return None
    except:
        return None

# 執行獲取
df = get_finmind_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 顯示邏輯
if df is not None and not df.empty:
    last = df.iloc[-1]
    c, h, l = float(last['Close']), float(last['High']), float(last['Low'])
    diff = h - l
    
    st.success(f"✅ {selected_label} 通道已導通")
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價", f"{c:,.2f}")
    col2.metric("高點", f"{h:,.2f}")
    col3.metric("低點", f"{l:,.2f}")
    
    st.divider()
    # 強哥核心：點位計算
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
    
    # 走勢圖
    chart_data = df.set_index('Date')['Close']
    st.line_chart(chart_data)
else:
    st.error("❌ 數據源連線中，請稍候或檢查代碼是否存在。")
