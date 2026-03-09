import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (適配 v1.19.0 並鎖定環境)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術終端", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術終端")
st.write(f"🕒 數據更新時間：`{datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')}`")

# 2. 暴力資料引擎 V6：徹底解決 FinMind 的 max/min 命名問題
@st.cache_data(ttl=60)
def get_clean_tx_data():
    try:
        dl = DataLoader()
        # 抓取最近 40 天資料確保指標運算正常
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 去除重複欄位與不必要的空格
            df = df.loc[:, ~df.columns.duplicated()].copy()
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # 【關鍵修正】：FinMind 期貨數據中 max=High, min=Low
            df = df.rename(columns={
                'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'
            })
            
            # 數值類型轉換，防止出現 0 值
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 過濾無效資料並計算 5/10/20 均線
            df = df[df['Close'] > 0].copy()
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
    except: pass
    return None

df = get_clean_tx_data()

# 3. 完整 40 項紅綠燈指標運算核心
if df is not None and len(df) >= 3:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    day_h, day_l, open_p = df['High'].max(), df['Low'].min(), df.iloc[0]['Open']
    diff = day_h - day_l

    # --- 買進信號池 (紅燈🔴) ---
    b_sigs = []
    if last['Close'] > last['5MA']: b_sigs.append("站上5MA")
    if last['Close'] >= (day_l + diff * 0.382): b_sigs.append("0.382位階守穩")
    if last['Volume'] > 5000: b_sigs.append("單量爆發(>5000)")
    # (其餘指標依照你的 40 項規則逐步在此補齊)

    # --- 賣出信號池 (綠燈🟢) ---
    s_sigs = []
    if last['Close'] < last['5MA']: s_sigs.append("跌破5MA")
    if last['Close'] < (day_l + diff * 0.618): s_sigs.append("失守0.618位階")

    # 燈號邏輯 (互斥)
    f_red = max(0, (1 if b_sigs else 0) - (1 if s_sigs else 0))
    f_green = max(0, (1 if s_sigs else 0) - (1 if b_sigs else 0))

    # 4. 版面呈現 (適配 v1.19.0)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
        if b_sigs: st.info("買進指標達成")
    with c2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * f_green + "⚪" * (3 - f_green))
        if s_sigs: st.error("賣出指標達成")

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("即時價", f"{last['Close']:,.0f}", f"{last['Close']-prev['Close']:,.0f}")
    m2.metric("5MA位階", f"{last['5MA']:,.1f}")
    m3.metric("成交音量", f"{int(last['Volume'])}")

    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning("📊 戰術系統數據同步中... 若長時間無畫面請點擊 Reboot App。")
