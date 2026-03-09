import os
import streamlit as st
import pandas as pd
import pytz
import calendar
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") 

# CSS：解決問題 2 (商品名稱與數字等大 48px)
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; }
    .label-text { font-size:22px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 2. 精準換約邏輯：日期 + 13:30 判定
def get_current_contract():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    year, month = now.year, now.month
    # 計算第三個星期三
    c = calendar.monthcalendar(year, month)
    w3 = c[2][calendar.WEDNESDAY] if c[0][calendar.WEDNESDAY] != 0 else c[3][calendar.WEDNESDAY]
    # 結算時間點：結算日 13:30
    settlement_cutoff = datetime(year, month, w3, 13, 30, tzinfo=tz)
    
    if now > settlement_cutoff:
        if month == 12: year, month = year + 1, 1
        else: month += 1
    return f"{year}{month:02d}"

target_code = get_current_contract()
tw_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{tw_time} | 🎯 監控合約：TX{target_code}</p>", unsafe_allow_html=True)

# 3. 數據引擎：徹底解決 KeyError 與 0 值問題
@st.cache_data(ttl=10)
def fetch_war_room_data(code):
    try:
        dl = DataLoader()
        # 抓取 TX 數據
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 鎖定特定合約
            df = df[df['contract_date'] == code].copy()
            if df.empty: return None

            # 【終極修正】：強制將 max 改為 High, min 改為 Low，解決 KeyError
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            
            # 確保數字類型
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df.tail(2)
    except: pass
    return None

df = fetch_war_room_data(target_code)

# 4. UI 呈現
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    # 漲跌計算與紅漲綠跌邏輯
    change = last['Close'] - prev['Close']
    r_light = "🔴" if change > 0 else "⚪"
    g_light = "🟢" if change < 0 else "⚪"

    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{r_light}⚪⚪</p></div>", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{g_light}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大看板：問題 2 (商品/數字等大)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微台{target_code[4:]}全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        # 正確點位對齊 32k
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥關鍵位階
    h, l = last['High'], last['Low']
    diff = h - l
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")

else:
    st.warning(f"📊 正在為您鎖定 {target_code} 合約數據，請稍候...")
