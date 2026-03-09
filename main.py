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

# 2. 數據引擎：暴力格式化欄位名稱，徹底消滅 KeyError
@st.cache_data(ttl=60)
def get_verified_data():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 【暴力對齊關鍵】：將所有欄位轉小寫、清除空格
            df.columns = [str(col).lower().strip() for col in df.columns]
            
            # 手動將我們需要的欄位對齊到大寫，確保後續邏輯不變
            rename_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
            df = df.rename(columns=rename_map)
            
            # 均線計算
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
        return None
    except Exception as e:
        st.error(f"數據讀取失敗: {e}")
        return None

df = get_verified_data()

# 3. 邏輯判定 (加入檢查，確保 df 包含必要欄位)
if df is not None and 'High' in df.columns:
    last = df.iloc[-1]
    day_h = df['High'].max() # 現在 High 絕對能被找到
    day_l = df['Low'].min()
    diff = day_h - day_l
    
    # 信號判斷
    b_sigs = []
    if last['Close'] > last['5MA']: b_sigs.append("5MA之上")
    
    s_sigs = []
    if last['Close'] < last['5MA']: s_sigs.append("跌破5MA")

    # 4. 看板呈現
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" if b_sigs else "⚪")
    with c2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" if s_sigs else "⚪")

    st.markdown("---")
    st.metric("即時點位", f"{last['Close']:,.0f}")
    st.error(f"🚀 壓力區 (0.618)：{day_l + diff * 0.618:,.2f}")
    st.info(f"🛡️ 支撐區 (0.382)：{day_l + diff * 0.382:,.2f}")

else:
    st.warning("⚠️ 數據對齊中... 請檢查日誌或點擊 Reboot App。")
