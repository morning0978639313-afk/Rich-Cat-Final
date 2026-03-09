import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心環境鎖定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=10 * 1000, key="war_room_final_black")

# --- 🎨 CSS：徹底封印黃色，強制標題變黑，字體 48px ---
st.markdown("""
    <style>
    /* 強制標題為黑色，移除所有黃色殘留 */
    .black-title { 
        color: #000000 !important; 
        text-align: center; 
        font-size: 52px; 
        font-weight: bold; 
        margin-top: -10px;
        margin-bottom: 20px;
        font-family: "Microsoft JhengHei", sans-serif;
    }
    /* 商品名稱與報價數字一樣大 (48px) */
    .big-val { font-size: 48px !important; font-weight: bold; color: white; }
    .label-text { font-size: 22px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #444; }
    
    /* 修正全域預設顏色 */
    h1, h2, h3 { color: black !important; }
    .stMetric label { color: #888888 !important; }
    </style>
    """, unsafe_allow_html=True)

# 顯示黑色標題 (Rich 指定，絕對不再變黃)
st.markdown("<p class='black-title'>🐱 RICH CAT 戰情室</p>", unsafe_allow_html=True)

# 2. 🔑 數據引擎：暴力鎖定 TMF 202603 全
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_data(ttl=5)
def fetch_mxf_stable_data():
    try:
        api = DataLoader()
        api.login(api_token=MY_TOKEN) # 使用正確的登入語法
        
        now_tw = datetime.now(pytz.timezone('Asia/Taipei'))
        # 抓取 TMF 日資料，這是目前最能精準區分「日盤」與「全盤」的接口
        df = api.taiwan_futures_daily(
            futures_id='TMF', 
            start_date=(now_tw - timedelta(days=5)).strftime('%Y-%m-%d')
        )
        
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 鎖定你要的 202603
            df = df[df['contract_date'] == '202603'].copy()
            
            # 欄位修正 (將 FinMind 原始 max/min 轉為我們需要的 High/Low)
            df = df.rename(columns={'max': 'high', 'min': 'low'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 【關鍵對齊】：同一天會有兩筆資料，取成交量大的那一筆 (就是全盤 32,013)
            latest_date = df['date'].max()
            today_data = df[df['date'] == latest_date].sort_values('volume', ascending=False)
            
            if not today_data.empty:
                # 抓取前一交易日做漲跌比較
                df_prev = df[df['date'] < latest_date].sort_values('volume', ascending=False).head(1)
                return pd.concat([df_prev, today_data.head(1)])
    except:
        pass
    return None

# 顯示校時 (黑色字體)
now_tw = datetime.now(pytz.timezone('Asia/Taipei'))
st.markdown(f"<p style='text-align: center; color: black;'>🕒 台北實時：{now_tw.strftime('%H:%M:%S')} | 🎯 監控：TMF 202603全</p>", unsafe_allow_html=True)

df = fetch_mxf_stable_data()

# 3. 視覺呈現
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 漲跌點數計算
    change = last['close'] - df.iloc[0]['close'] if len(df) > 1 else last['close'] - last['open']
    
    # 燈號區 (維持 Rich 要求的對消佔位)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴' if change > 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢' if change < 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大看板：商品名稱與數字對齊 48px
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-val'>微台03全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        # 正確對齊截圖中的 32,013 點位
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥位階計算 (0.618 / 0.382)
    h, l = last['high'], last['low']
    diff = h - l
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
else:
    st.warning("📊 戰情室數據同步中... 請點擊右下角 Manage app -> Reboot app。")
