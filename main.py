import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境與 UI 鎖定 (適配 1.19.0)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") # 15秒刷新

# 問題 2 解決：CSS 強制讓文字與報價數字一樣大
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; color: white; }
    .label-text { font-size:20px; color: #BBBBBB; margin-bottom: -15px; }
    .center-box { text-align: center; background-color: #1E1E1E; padding: 20px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 問題 1 解決：標題改為 RICH CAT 戰情室
st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 顯示台北實時時間
now_tw = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{now_tw}</p>", unsafe_allow_html=True)

# 2. 數據引擎：問題 3 解決 (鎖定 32k 點位，過濾主力合約)
@st.cache_data(ttl=10)
def get_real_tx_data():
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
            
            # 只取最新日期的資料
            latest_date = df['date'].max()
            df = df[df['date'] == latest_date].copy()
            
            # 轉換數值並取成交量最大者 (主力合約)
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.sort_values('Volume', ascending=False).head(1)
            return df
    except: pass
    return None

df = get_real_tx_data()

# 3. 畫面呈現
if df is not None and not df.empty:
    last = df.iloc[0]
    
    # 漲跌與燈號計算
    change = last['Close'] - last['Open']
    r_light = "🔴" if change > 0 else "⚪"
    g_light = "🟢" if change < 0 else "⚪"

    # 燈號區 (維持 3 顆點)
    l_col, r_col = st.columns(2)
    with l_col:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{r_light}⚪⚪</p></div>", unsafe_allow_html=True)
    with r_col:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{g_light}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標區：問題 2 (名稱與數字等大)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微台近全</p>", unsafe_allow_html=True)
    with m2:
        # 問題 5 修正：漲必紅，跌必綠
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        # 問題 3 解決：正確點位 (32,xxx)
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥位階
    day_h, day_l = last['High'], last['Low']
    diff = day_h - day_l
    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning("📊 戰情室數據重新定位中... 請點擊右下角 Reboot App。")
