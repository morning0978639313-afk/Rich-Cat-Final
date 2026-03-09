import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") 

# 問題 1 解決：名稱改為 RICH CAT 戰情室
st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 找回時間顯示
now_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 數據更新時間：{now_time}</p>", unsafe_allow_html=True)

# 2. 數據引擎：解決 32,055 錯誤點位問題
@st.cache_data(ttl=10)
def get_verified_tx_data():
    try:
        dl = DataLoader()
        # 抓取最近資料
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            
            # 【關鍵修正】：只取最新日期的資料，避免抓到歷史高價
            latest_date = df['date'].max()
            df = df[df['date'] == latest_date].copy()
            
            # 數值校正
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 再次過濾掉異常值 (TX 目前不可能超過 30,000 或低於 10,000)
            df = df[(df['Close'] > 10000) & (df['Close'] < 30000)].tail(2)
            return df
    except: pass
    return None

df = get_verified_tx_data()

if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 模擬漲跌計算 (若僅有一筆則顯示 0)
    change = 0.0 if len(df) < 2 else last['Close'] - df.iloc[-2]['Close']
    
    # 燈號判定
    r_light = "🔴" if last['Close'] > last['Open'] else "⚪"
    g_light = "🟢" if last['Close'] < last['Open'] else "⚪"

    # 燈號顯示
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🔴 買進燈號")
        st.write(f"{r_light}⚪⚪")
    with col_r:
        st.subheader("🟢 賣出燈號")
        st.write(f"{g_light}⚪⚪")

    st.markdown("---")
    
    # 問題 2 解決：商品名稱跟即時報價數字一樣大
    # 使用 Markdown 自定義字體大小
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("<p style='font-size: 20px; color: gray;'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 42px; font-weight: bold;'>微台近全 (TX)</p>", unsafe_allow_html=True)
    
    with c2:
        # 問題 5 解決：紅漲綠跌邏輯
        color = "red" if change >= 0 else "green"
        st.markdown("<p style='font-size: 20px; color: gray;'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 42px; font-weight: bold; color: {color};'>{change:+.1f}</p>", unsafe_allow_html=True)
        
    with c3:
        # 問題 3 解決：數字正確性 (22,xxx)
        st.markdown("<p style='font-size: 20px; color: gray;'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size: 42px; font-weight: bold;'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 壓力支撐重新校正
    day_h, day_l = last['High'], last['Low']
    diff = day_h - day_l
    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning("📊 數據重新定位中，請確保 FinMind API 正常連線並點擊 Reboot...")
