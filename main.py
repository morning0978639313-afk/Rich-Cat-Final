import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=10 * 1000, key="war_room_final")

# --- 🎨 CSS：徹底封印黃色，強制黑色標題 ---
st.markdown("""
    <style>
    .black-title { 
        color: #000000 !important; 
        text-align: center; 
        font-size: 52px; 
        font-weight: bold; 
        margin-top: -20px;
        font-family: "Microsoft JhengHei", sans-serif;
    }
    .big-val { font-size: 48px !important; font-weight: bold; color: white; }
    .label-text { font-size: 22px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #444; }
    /* 修正全域標題顏色預設值 */
    h1 { color: black !important; }
    </style>
    """, unsafe_allow_html=True)

# 顯示黑色標題 (Rich 指定)
st.markdown("<p class='black-title'>🐱 RICH CAT 戰情室</p>", unsafe_allow_html=True)

# 2. 🔑 數據引擎：暴力鎖定 TMF 202603 全
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_data(ttl=5)
def fetch_mxf_stable_data():
    try:
        api = DataLoader()
        api.login(api_token=MY_TOKEN)
        
        now_tw = datetime.now(pytz.timezone('Asia/Taipei'))
        # 使用 daily 接口通常比 tick 穩定，且能區分全盤
        df = api.taiwan_futures_daily(
            futures_id='TMF', 
            start_date=(now_tw - timedelta(days=5)).strftime('%Y-%m-%d')
        )
        
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 鎖定 202603
            df = df[df['contract_date'] == '202603'].copy()
            
            # 欄位修正 (FinMind 原始 max/min 轉為程式需要的 High/Low)
            df = df.rename(columns={'max': 'high', 'min': 'low'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 【核心邏輯】：取成交量最大的一筆 (全日盤)，對齊你截圖中的 32,013
            latest_date = df['date'].max()
            today_data = df[df['date'] == latest_date].sort_values('volume', ascending=False)
            
            if len(today_data) >= 1:
                # 抓取前一筆做漲跌比對
                df_prev = df[df['date'] < latest_date].sort_values('volume', ascending=False).head(1)
                return pd.concat([df_prev, today_data.head(1)])
    except Exception as e:
        st.sidebar.error(f"API 抓取細節錯誤: {e}")
    return None

# 顯示校時 (黑色文字)
now_tw = datetime.now(pytz.timezone('Asia/Taipei'))
st.markdown(f"<p style='text-align: center; color: black;'>🕒 台北實時：{now_tw.strftime('%H:%M:%S')} | 🎯 監控：TMF 202603全</p>", unsafe_allow_html=True)

df = fetch_mxf_stable_data()

# 3. 視覺呈現
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

    # 三大指標：微台03全與點位對齊 48px
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-val'>微台03全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥關鍵位階計算
    h, l = last['high'], last['low']
    diff = h - l
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
else:
    st.warning("📊 戰情室數據同步中... 若持續無數字，請確認 FinMind 帳號是否正常。")
