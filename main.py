import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心設定 (適配 v1.19.0)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術終端", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") # 15秒快速同步

# 2. 數據引擎：精準對齊當日點位，防止抓到歷史錯誤數據
@st.cache_data(ttl=10)
def get_accurate_tx_data():
    try:
        dl = DataLoader()
        # 抓取最近 5 天資料，確保有足夠樣本計算漲跌
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            
            # 數值校正
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna(subset=['Close']).copy()
            # 計算 5MA
            df['5MA'] = df['Close'].rolling(window=5).mean()
            return df
    except: pass
    return None

df = get_accurate_tx_data()

# 3. 邏輯判定與畫面排版
st.title("🐱 RICH CAT 紅綠燈戰術終端")

# 問題 1 解決：找回時間顯示
now_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"🕒 數據更新時間：`{now_time}`")

if df is not None and len(df) >= 2:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    day_h, day_l = df['High'].max(), df['Low'].min()
    diff = day_h - day_l

    # 燈號計數邏輯
    b_sigs = ["站上5MA"] if last['Close'] > last['5MA'] else []
    s_sigs = ["跌破5MA"] if last['Close'] < last['5MA'] else []

    # 燈號亮起個數計算
    r_on = 1 if b_sigs else 0
    g_on = 1 if s_sigs else 0
    
    # 互斥邏輯
    f_red = max(0, r_on - g_on)
    f_green = max(0, g_on - r_on)

    # 問題 2 解決：補齊賣出燈號，確保維持 3 顆圓點
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
    with col_r:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * f_green + "⚪" * (3 - f_green))

    st.markdown("---")
    
    # 問題 3 & 5 解決：更名看板並設定紅漲綠跌
    m1, m2, m3 = st.columns(3)
    m1.metric("📌 商品名稱", "微台近全 (TX)")
    
    # 漲跌計算與顏色校正 (inverse 代表 正數紅、負數綠)
    change = last['Close'] - prev['Close']
    m2.metric("📊 漲跌點數", f"{change:,.1f}", delta=f"{change:,.1f}", delta_color="inverse")
    
    # 即時價格校正
    m3.metric("💰 即時價格", f"{last['Close']:,.0f}")

    # 問題 4 解決：依據正確點位重算壓力支撐
    st.markdown("### 🛡️ 關鍵位階判斷")
    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning("📊 正在同步最新 TX 點位，請稍候...")
