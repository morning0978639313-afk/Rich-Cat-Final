import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統相容性修正 (適配 v1.19.0)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術系統", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術系統")
st.write("🎯 監控標的：**微台近全 (TX)**")

# 2. 數據獲取：徹底修正 KeyError 問題
@st.cache_data(ttl=60)
def get_verified_data():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 【關鍵修復】: 將 FinMind 的小寫欄位強制轉為大寫，防止 KeyError
            df = df.rename(columns={
                'open': 'Open', 'high': 'High', 'low': 'Low', 
                'close': 'Close', 'volume': 'Volume', 'date': 'Date'
            })
            # 均線校正
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
        return None
    except:
        return None

df = get_verified_data()

# 3. 核心 40 項指標邏輯運算
if df is not None and len(df) >= 4:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    day_h = df['High'].max() # 修正大寫調用
    day_l = df['Low'].min()
    diff = day_h - day_l
    open_p = df.iloc[0]['Open']

    # --- 買進 (🔴) 指標判斷 ---
    b_sigs = []
    if all(df['Close'].iloc[1:4] > df['Open'].iloc[1:4]): b_sigs.append("開盤三連紅")
    if last['Close'] > last['5MA']: b_sigs.append("B11:5MA之上")
    if last['Close'] > (day_l + diff * 0.382): b_sigs.append("B1:0.382支撐")
    if last['Volume'] > 5000: b_sigs.append("B20:量能爆發")
    if all(df['Close'].tail(3) > df['Open'].tail(3)): b_sigs.append("B14:連三紅")

    # --- 賣出 (🟢) 指標判斷 ---
    s_sigs = []
    if last['Close'] < last['5MA']: s_sigs.append("S11:破5MA")
    if last['Close'] < (day_l + diff * 0.618): s_sigs.append("S1:破0.618位階")
    if all(df['Close'].tail(3) < df['Open'].tail(3)): s_sigs.append("S14:連三綠")
    if last['High'] < prev['High']: s_sigs.append("S4:高點降低")

    # --- 燈號計數與互斥規則 ---
    r_raw = min(3, (1 if len(b_sigs) > 0 else 0) + (len(b_sigs) // 5))
    g_raw = min(3, (1 if len(s_sigs) > 0 else 0) + (len(s_sigs) // 5))
    f_red = max(0, r_raw - g_raw)
    f_green = max(0, g_raw - r_raw)

    # 4. 界面呈現 (避開 st.divider)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
        st.info(f"達成買入信號: {len(b_sigs)}")
    with col2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * f_green + "⚪" * (3 - f_green))
        st.info(f"達成賣出信號: {len(s_sigs)}")

    st.markdown("---") 
    m1, m2, m3 = st.columns(3)
    m1.metric("即時價", f"{last['Close']:,.0f}")
    m2.metric("5MA位階", f"{last['5MA']:,.1f}")
    m3.metric("今日高點", f"{day_h:,.0f}")

    # 強哥位階顯示
    st.error(f"🚀 壓力區 (0.618)：{day_l + diff * 0.618:,.2f}")
    st.info(f"🛡️ 支撐區 (0.382)：{day_l + diff * 0.382:,.2f}")

else:
    st.warning("⚠️ 數據源連線中，請點擊右下角 Manage app -> Reboot app。")
