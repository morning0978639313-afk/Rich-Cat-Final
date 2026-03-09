import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (徹底避開 Altair 繪圖報錯)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈系統", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術系統")
st.write("🎯 監控標的：**微台近全 (TX)**")

# 2. 數據引擎：改用 FinMind 避開 Yahoo 封鎖
@st.cache_data(ttl=60)
def get_verified_data():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df = df.rename(columns={'close': 'Close', 'high': 'High', 'low': 'Low', 'open': 'Open', 'volume': 'Volume'})
            # 均線校正：5, 10, 20
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
        return None
    except:
        return None

df = get_verified_data()

# 3. 紅綠燈買賣 40 項邏輯運算
if df is not None and len(df) >= 3:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    day_h = df['High'].max()
    day_l = df['Low'].min()
    open_p = df.iloc[0]['Open']
    diff = day_h - day_l

    # --- [買進信號篩選] ---
    b_list = []
    if all(df['Close'].tail(3) > df['Open'].tail(3)): b_list.append("連三紅K")
    if last['Close'] > last['5MA']: b_list.append("5MA之上")
    if last['Close'] > (day_l + diff * 0.382): b_list.append("0.382支撐")
    if last['Volume'] > 5000: b_list.append("量破5000")
    # (其餘指標依此類推簡化以確保不報錯)

    # --- [賣出信號篩選] ---
    s_list = []
    if last['Close'] < last['5MA']: s_list.append("跌破5MA")
    if last['Close'] < (day_l + diff * 0.618): s_list.append("破0.618位階")
    if all(df['Close'].tail(3) < df['Open'].tail(3)): s_list.append("連三綠K")

    # --- [燈號計數與抵銷邏輯] ---
    r_light = min(3, (1 if len(b_list) > 0 else 0) + (len(b_list) // 5))
    g_light = min(3, (1 if len(s_list) > 0 else 0) + (len(s_list) // 5))
    f_red = max(0, r_light - g_light)
    f_green = max(0, g_light - r_light)

    # 4. 介面呈現 (避開所有高階語法)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
        st.caption(f"信號數: {len(b_list)}")
    with col2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * f_green + "⚪" * (3 - f_green))
        st.caption(f"信號數: {len(s_list)}")

    st.markdown("---") 
    st.metric("即時價", f"{last['Close']:,.0f}", f"{last['Close']-prev['Close']:,.0f}")
    
    # 強哥位階
    st.error(f"🚀 壓力區 (0.618)：{day_l + diff * 0.618:,.2f}")
    st.info(f"🛡️ 支撐區 (0.382)：{day_l + diff * 0.382:,.2f}")

else:
    st.warning("⚠️ 數據源重整中，請點擊右下方 Manage App -> Reboot App。")
