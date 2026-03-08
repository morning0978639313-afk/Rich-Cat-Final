import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 強制設定環境變數
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

st.set_page_config(page_title="Rich 戰情室")
st.title("🐱 08:45 準時開盤戰情室")

# 商品設定
SYMBOL_MAP = {"加權指數": "^TWII")

# 抓取數據 (不使用 altair 繪圖，純文字顯示最穩)
df = yf.download(SYMBOL_MAP[target], period="5d", progress=False)

if not df.empty:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    last = df.iloc[-1]
    c, h, l = float(last['Close']), float(last['High']), float(last['Low'])
    diff = h - l
    
    # 計算點位
    st.metric(f"當前 {target}", f"{c:,.2f}")
    st.error(f"🚀 壓力位 (0.618): {l + diff * 0.618:,.2f}")
    st.info(f"⚖️ 多空中軸 (0.500): {l + diff * 0.500:,.2f}")
    st.success(f"🛡️ 支撐位 (0.382): {l + diff * 0.382:,.2f}")
    
    tz = pytz.timezone('Asia/Taipei')
    st.write(f"最後更新：{datetime.now(tz).strftime('%H:%M:%S')}")
