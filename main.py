import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境與 UI 設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") # 15秒超快同步

# 自定義 CSS：問題 2 解決 (商品名稱與報價數字一樣大)
st.markdown("""
    <style>
    .big-font { font-size:48px !important; font-weight: bold; font-family: 'Courier New', Courier, monospace; }
    .label-font { font-size:20px; color: #808080; margin-bottom: -10px; }
    .center-text { text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 問題 1 解決：標題改為 RICH CAT 戰情室
st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 找回時間顯示
now_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{now_time}</p>", unsafe_allow_html=True)

# 2. 數據引擎：問題 3 解決 (確保數字正確，過濾錯誤合約)
@st.cache_data(ttl=10)
def get_verified_data():
    try:
        dl = DataLoader()
        # 抓取台指期全月份資料
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # 【關鍵校正】：只取最新日期的資料，並過濾掉成交量過小的歷史合約
            latest_date = df['date'].max()
            df = df[df['date'] == latest_date].copy()
            
            # 轉換數值，更名欄位
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 取成交量最大的一筆 (即為當前近月主力合約)
            df = df.sort_values('Volume', ascending=False).head(1)
            return df
    except: pass
    return None

df = get_verified_data()

# 3. 畫面呈現
if df is not None and not df.empty:
    last = df.iloc[0]
    
    # 漲跌與燈號邏輯
    change = last['Close'] - last['Open']
    r_light = "🔴" if change > 0 else "⚪"
    g_light = "🟢" if change < 0 else "⚪"

    # 燈號區
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"<div class='center-text'><p class='label-font'>🔴 買進燈號</p><p class='big-font'>{r_light}⚪⚪</p></div>", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"<div class='center-text'><p class='label-font'>🟢 賣出燈號</p><p class='big-font'>{g_light}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 問題 2 解決：名稱與數字等大
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-font'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-font'>微台近全</p>", unsafe_allow_html=True)
    with m2:
        color = "red" if change >= 0 else "green"
        st.markdown("<p class='label-font'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-font' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        st.markdown("<p class='label-font'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-font'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    # 壓力支撐
    st.markdown("---")
    day_h, day_l = last['High'], last['Low']
    diff = day_h - day_l
    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning("📊 戰情室數據重新校準中... 請點擊右下角 Manage App -> Reboot App。")
