import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境設定 (針對 Python 3.14 與 v1.35+ 優化)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=10 * 1000, key="war_room_refresh")

# --- 🎨 CSS 樣式控制：強制標題變黑 ---
st.markdown("""
    <style>
    /* 強制標題為黑色 */
    .black-title { 
        color: #000000 !important; 
        text-align: center; 
        font-size: 52px; 
        font-weight: bold; 
        margin-top: -20px;
    }
    .big-val { font-size: 48px !important; font-weight: bold; color: white; }
    .label-text { font-size: 20px; color: #888888; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_html=True)

# 顯示黑色標題
st.markdown("<p class='black-title'>🐱 RICH CAT 戰情室</p>", unsafe_allow_html=True)

# 2. 🔑 數據引擎：鎖定 TMF 202603 全
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_data(ttl=5)
def fetch_mxf_full_data():
    try:
        api = DataLoader()
        api.login(api_token=MY_TOKEN)
        
        now_tw = datetime.now(pytz.timezone('Asia/Taipei'))
        # 抓取 TMF 資料，包含夜盤
        df = api.taiwan_futures_daily(
            futures_id='TMF', 
            start_date=(now_tw - timedelta(days=5)).strftime('%Y-%m-%d')
        )
        
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 鎖定 202603 合約
            df = df[df['contract_date'] == '202603'].copy()
            
            # 欄位修正 (max/min -> high/low)
            df = df.rename(columns={'max': 'high', 'min': 'low'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 取最新成交量最大的一筆 (全盤)
            latest_date = df['date'].max()
            df_latest = df[df['date'] == latest_date].sort_values('volume', ascending=False).head(1)
            df_prev = df[df['date'] < latest_date].sort_values('volume', ascending=False).tail(1)
            return pd.concat([df_prev, df_latest])
    except:
        pass
    return None

# 顯示校時
now_str = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')
st.markdown(f"<p style='text-align: center; color: black;'>🕒 台北實時：{now_str} | 🎯 監控：TMF 202603全</p>", unsafe_allow_html=True)

df = fetch_rich_cat_data = fetch_mxf_full_data()

# 3. 畫面呈獻
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    change = last['close'] - df.iloc[0]['close'] if len(df) > 1 else last['close'] - last['open']
    
    # 燈號區 (對消邏輯：後進訊號扣除對方存量)
    # 這裡實作基本的紅/綠判定，若要細化到 20+20 指標可再加入
    r_light = "🔴" if change > 0 else "⚪"
    g_light = "🟢" if change < 0 else "⚪"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{r_light}⚪⚪</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{g_light}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標：商品名稱與報價文字大小對齊 (48px)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-val'>微台03全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        # 對齊截圖中的 32,013 點位
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥位階計算
    diff = last['high'] - last['low']
    st.error(f"🚀 壓力區 (0.618)：**{last['low'] + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{last['low'] + diff * 0.382:,.2f}**")
else:
    st.warning("📊 數據重新鎖定中，請點擊右下角 Reboot App。")
