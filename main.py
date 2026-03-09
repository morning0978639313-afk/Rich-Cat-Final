import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (解決 Python 3.14 的環境崩潰問題)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=10 * 1000, key="datarefresh") # 10秒快同步

# CSS：解決「商品名稱與數字等大」 (48px) + 黃色標題
st.markdown("""
    <style>
    .yellow-title { color: #FFFF00 !important; text-align: center; font-size: 48px; font-weight: bold; margin-bottom: 20px; }
    .big-val { font-size: 48px !important; font-weight: bold; color: white; }
    .label-text { font-size: 22px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #444; }
    </style>
    """, unsafe_allow_html=True)

# 強制顯示黑色標題
st.markdown("<p class='yellow-title'>🐱 RICH CAT 戰情室</p>", unsafe_allow_html=True)

# 2. 🔑 Token 與 數據引擎 (鎖定 TMF 202603)
MY_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wMy0wOSAyMDozOToxOSIsInVzZXJfaWQiOiJhcmljYTUxNSIsImVtYWlsIjoiZXZlbmNoZW41MTVAZ21haWwuY29tIiwiaXAiOiIxMjQuNi4xMS4yMTYifQ.NkLHnTiAp10uKfrc8qkt0YevD-Cc1XV062O1u3lBvh4"

@st.cache_data(ttl=5)
def fetch_rich_cat_data():
    try:
        api = DataLoader()
        api.login(api_token=MY_TOKEN)
        
        # 抓取微台資料
        now_tw = datetime.now(pytz.timezone('Asia/Taipei'))
        df = api.taiwan_futures_daily(
            futures_id='TMF', 
            start_date=(now_tw - timedelta(days=5)).strftime('%Y-%m-%d')
        )
        
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 【硬鎖定】：只要 202603 合約
            df = df[df['contract_date'] == '202603'].copy()
            
            # 欄位校正
            df = df.rename(columns={'max': 'high', 'min': 'low'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 【關鍵】：取最新日期中成交量最大的，就是你要的「全盤」32,013
            latest_date = df['date'].max()
            df_latest = df[df['date'] == latest_date].sort_values('volume', ascending=False).head(1)
            df_prev = df[df['date'] < latest_date].sort_values('volume', ascending=False).tail(1)
            return pd.concat([df_prev, df_latest])
    except:
        pass
    return None

# 顯示台北實時
now_str = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{now_str} | 🎯 監控：TMF 202603全</p>", unsafe_allow_html=True)

df = fetch_rich_cat_data()

# 3. 視覺呈現
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 計算漲跌
    change = last['close'] - df.iloc[0]['close'] if len(df) > 1 else last['close'] - last['open']
    
    # 燈號區 (根據 Rich 的邏輯)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴' if change > 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢' if change < 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大看板：字體統一放大 48px
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown("<p class='big-val'>微台03全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100" # 紅漲綠跌
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 位階計算
    diff = last['high'] - last['low']
    st.error(f"🚀 壓力區 (0.618)：**{last['low'] + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{last['low'] + diff * 0.382:,.2f}**")
else:
    st.warning("📊 正在同步 TMF202603 全盤數據... 請確認後點擊 Reboot。")
