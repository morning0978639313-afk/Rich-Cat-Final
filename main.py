import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (徹底避開 Altair 報錯)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈系統", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術系統")
st.write("🎯 監控標的：**微台近全 (TX)**")

# 2. 數據引擎：修正欄位名稱轉換邏輯
@st.cache_data(ttl=60)
def get_verified_data():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 【修正關鍵】：將 FinMind 的小寫欄位強制轉為大寫，避免 KeyError
            df = df.rename(columns={
                'open': 'Open', 
                'high': 'High', 
                'low': 'Low', 
                'close': 'Close', 
                'volume': 'Volume'
            })
            # 均線校正
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
        return None
    except Exception as e:
        st.error(f"數據讀取失敗: {e}")
        return None

df = get_verified_data()

# 3. 紅綠燈邏輯 (加入資料檢查，避免當機)
if df is not None and len(df) >= 5:
    # 確保抓到的是今天的資料
    last = df.iloc[-1]
    prev = df.iloc[-2]
    day_h = df['High'].max()
    day_l = df['Low'].min()
    diff = day_h - day_l
    
    # 買進/賣出信號計算 (簡化示範)
    b_sigs = []
    if last['Close'] > last['5MA']: b_sigs.append("5MA之上")
    if last['Close'] > (day_l + diff * 0.382): b_sigs.append("0.382支撐")
    
    s_sigs = []
    if last['Close'] < last['5MA']: s_sigs.append("跌破5MA")
    
    # 燈號互斥
    f_red = max(0, (1 if b_sigs else 0) - (1 if s_sigs else 0))
    f_green = max(0, (1 if s_sigs else 0) - (1 if b_sigs else 0))

    # 4. 介面呈現
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
    with c2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * f_green + "⚪" * (3 - f_green))

    st.markdown("---")
    m1, m2 = st.columns(2)
    m1.metric("即時點位", f"{last['Close']:,.0f}")
    m2.metric("今日振幅", f"{diff:,.0f}")

else:
    st.warning("⚠️ 目前抓不到 FinMind 的 TX 數據，請確認 API 是否正常或點擊 Reboot 重試。")
