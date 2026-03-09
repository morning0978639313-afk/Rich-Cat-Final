import os
import streamlit as st
import pandas as pd
import pytz
import calendar
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境與 UI 設定 (適配 v1.19.0)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") # 15秒刷新一次

# CSS：確保標籤字體與報價數字一樣大 (48px)
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; }
    .label-text { font-size:20px; color: #888888; margin-bottom: -10px; }
    .center-box { text-align: center; background: #111111; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 2. 自動結算邏輯：日期 + 時間 (13:30) 雙重判定
def get_verified_contract():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    year, month = now.year, now.month
    
    # 計算該月所有星期三
    c = calendar.monthcalendar(year, month)
    wednesdays = [week[calendar.WEDNESDAY] for week in c if week[calendar.WEDNESDAY] != 0]
    # 取第三個星期三作為結算日
    settlement_day = wednesdays[2]
    
    # 設定結算時間點：結算日當天 13:30
    settlement_time = datetime(year, month, settlement_day, 13, 30, tzinfo=tz)
    
    # 【關鍵判斷】：如果當下時間已超過結算點，則自動切換至下個月合約
    if now > settlement_time:
        if month == 12: 
            year, month = year + 1, 1
        else: 
            month += 1
            
    return f"{year}{month:02d}"

target_contract = get_verified_contract()

# 顯示台北實時與追蹤合約
now_tw = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{now_tw} | 🎯 當前鎖定合約：{target_contract}</p>", unsafe_allow_html=True)

# 3. 數據引擎：鎖定正確合約並排除 0 與 重複欄位
@st.cache_data(ttl=10)
def get_contract_data(code):
    try:
        dl = DataLoader()
        # 抓取最近 10 天資料以進行漲跌比對
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 過濾特定月份合約
            df = df[df['contract_date'] == code].copy()
            if df.empty: return None
            
            # 更名並去重
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            df = df.loc[:, ~df.columns.duplicated()].copy()
            
            # 數值校正，確保不為 0
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df.tail(2)
    except: pass
    return None

df = get_contract_data(target_contract)

# 4. 戰情室畫面呈現
if df is not None and not df.empty:
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    # 漲跌與紅漲綠跌邏輯
    change = last['Close'] - prev['Close']
    r_light = "🔴" if change > 0 else "⚪"
    g_light = "🟢" if change < 0 else "⚪"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{r_light}⚪⚪</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{g_light}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標看板：商品、漲跌、價格
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微台{target_contract[4:]}全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥位階計算
    day_h, day_l = last['High'], last['Low']
    diff = day_h - day_l
    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning(f"📊 正在等待市場開盤或鎖定 {target_contract} 數據...")
