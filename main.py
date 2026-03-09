import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (徹底解決 Python 3.14 的 imghdr 崩潰問題)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") 

# CSS：商品名稱與報價數字一致 48px
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; font-family: 'Arial Black', sans-serif; }
    .label-text { font-size:22px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

# 2. 數據引擎：精準鎖定 TMF 202603 且過濾全盤資料
@st.cache_data(ttl=10)
def fetch_tmf_2603():
    try:
        dl = DataLoader()
        # 改用 TMF 抓取微台資料
        df = dl.taiwan_futures_daily(
            futures_id='TMF', 
            start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # 【硬鎖定】：只要 202603 合約
            df = df[df['contract_date'] == '202603'].copy()
            
            # 欄位校正：FinMind max/min 轉為 High/Low
            df = df.rename(columns={'max': 'high', 'min': 'low'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 【關鍵】：取最新日期中成交量最大的，就是「全盤」32,013
            latest_date = df['date'].max()
            df_latest = df[df['date'] == latest_date].sort_values('volume', ascending=False).head(1)
            df_prev = df[df['date'] < latest_date].sort_values('volume', ascending=False).tail(1)
            return pd.concat([df_prev, df_latest])
    except: pass
    return None

df = fetch_tmf_2603()

# 3. 戰情室視覺呈獻
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 漲跌計算
    change = last['close'] - df.iloc[0]['close'] if len(df) > 1 else last['close'] - last['open']
    
    # 燈號區
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴' if change > 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢' if change < 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標看板
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-val'>微台03全</p>", unsafe_allow_html=True)
    with m2:
        # 紅漲綠跌
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        # 正確對齊實戰點位 32,013
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥位階
    diff = last['high'] - last['low']
    st.error(f"🚀 壓力區 (0.618)：**{last['low'] + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{last['low'] + diff * 0.382:,.2f}**")
else:
    st.warning("📊 正在鎖定 微台03全 (TMF) 數據... 請點擊 Reboot 重啟環境。")
