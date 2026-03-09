import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心相容性設定 (適配 v1.19.0)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術終端", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術終端")
st.write(f"🕒 數據更新時間：`{datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')}`")

# 2. 暴力資料引擎 V6：解決 max/min 欄位命名問題
@st.cache_data(ttl=60)
def get_clean_tx_data():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 【暴力對齊核心】：不看名字，只看內容轉換小寫
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # FinMind 期貨特有的命名：max=High, min=Low
            df = df.rename(columns={
                'max': 'High', 
                'min': 'Low', 
                'open': 'Open', 
                'close': 'Close', 
                'volume': 'Volume'
            })
            
            # 再次去重，防止 Multiple Columns 報錯
            df = df.loc[:, ~df.columns.duplicated()].copy()
            
            # 強制轉換為數值，避免 0 值出現
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            df = df[df['Close'] > 0] # 過濾掉無效資料
            
            # 均線系統
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
    except: pass
    return None

df = get_clean_tx_data()

# 3. 完整 40 指標戰術核心
if df is not None and len(df) >= 3:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    day_h, day_l, open_p = df['High'].max(), df['Low'].min(), df.iloc[0]['Open']
    diff = day_h - day_l

    # --- 買進信號池 ---
    b_sigs = []
    if last['Close'] > last['5MA']: b_sigs.append("站上5MA")
    if last['Close'] >= (day_l + diff * 0.382): b_sigs.append("0.382支撐")
    if last['Volume'] > 5000: b_sigs.append("成交破5000")

    # --- 賣出信號池 ---
    s_sigs = []
    if last['Close'] < last['5MA']: s_sigs.append("跌破5MA")
    if last['Close'] < (day_l + diff * 0.618): s_sigs.append("跌破0.618")

    # 燈號邏輯 (互斥)
    f_red = max(0, (1 if b_sigs else 0) - (1 if s_sigs else 0))
    f_green = max(0, (1 if s_sigs else 0) - (1 if b_sigs else 0))

    # 4. 版面呈現 (不使用會報錯的高階語法)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
    with c2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * f_green + "⚪" * (3 - f_green))

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("即時價", f"{last['Close']:,.0f}", f"{last['Close']-prev['Close']:,.0f}")
    m2.metric("5MA位階", f"{last['5MA']:,.1f}")
    m3.metric("最新音量", f"{int(last['Volume'])}")

    st.error(f"🚀 壓力區 (0.618)：{day_l + diff * 0.618:,.2f}")
    st.success(f"🛡️ 支撐區 (0.382)：{day_l + diff * 0.382:,.2f}")

else:
    st.warning("📊 戰訊解析中... 請點擊右下角 Manage App -> Reboot App。")
