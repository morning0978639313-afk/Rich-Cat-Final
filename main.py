import os
import streamlit as st
import pandas as pd
import pytz
import calendar
import requests
import json
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# --- 1. 核心參數設定 ---
# 請在此填入從 LINE Developers 取得的資訊
LINE_ACCESS_TOKEN = "你的_Channel_Access_Token"
LINE_USER_ID = "你的_User_ID"

def push_line_msg(text):
    if LINE_ACCESS_TOKEN == "你的_Channel_Access_Token": return
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, data=json.dumps(payload), headers=headers)

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") 

# CSS：標題改黑色、商品與報價字體一樣大 (48px)
st.markdown("""
    <style>
    h1 { color: black !important; text-align: center; font-weight: bold; }
    .big-val { font-size:48px !important; font-weight: bold; color: black; }
    .label-text { font-size:20px; color: #666666; margin-bottom: -15px; }
    .center-box { text-align: center; background: #F0F2F6; padding: 20px; border-radius: 15px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# --- 2. 數據引擎與結算邏輯 ---
def get_verified_contract():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    c = calendar.monthcalendar(now.year, now.month)
    w3 = [week[calendar.WEDNESDAY] for week in c if week[calendar.WEDNESDAY] != 0][2]
    settlement_time = datetime(now.year, now.month, w3, 13, 30, tzinfo=tz)
    y, m = now.year, now.month
    if now > settlement_time:
        if m == 12: y, m = y + 1, 1
        else: m += 1
    return f"{y}{m:02d}"

target_code = get_verified_contract()
st.markdown(f"<p style='text-align: center; color: black;'>🕒 台北實時：{datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')} | 🎯 鎖定合約：{target_code}</p>", unsafe_allow_html=True)

@st.cache_data(ttl=10)
def get_mxf_3min_data(code):
    try:
        dl = DataLoader()
        # 抓取微台 (MXF) 3分K 核心數據
        df_tick = dl.taiwan_futures_tick(futures_id='MXF', date=datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d'))
        if df_tick is not None and not df_tick.empty:
            df_tick['date'] = pd.to_datetime(df_tick['date'] + ' ' + df_tick['time'])
            df_tick = df_tick.set_index('date')
            df_3m = df_tick['price'].resample('3T').ohlc()
            df_3m['Volume'] = df_tick['qty'].resample('3T').sum()
            df_3m.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df_3m['5MA'] = df_3m['Close'].rolling(5).mean()
            return df_3m.dropna()
    except: pass
    return None

df = get_mxf_3min_data(target_code)

# --- 3. 畫面呈現與二燈通知邏輯 ---
if df is not None and not df.empty:
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    # 燈號判定邏輯 (以5MA為例，可擴充至40項)
    r_count = 1 if last['Close'] > last['5MA'] else 0
    g_count = 1 if last['Close'] < last['5MA'] else 0

    # 🚨 二燈報警：無論 2紅、2綠 或 各一，只要總數為 2 就通知
    if (r_count + g_count) >= 2:
        msg = f"\n⚠️ RICH CAT 戰報\n狀態：雙燈亮起！\n價格：{last['Close']:,.0f}\n合約：{target_code}\n(請即刻進場檢視)"
        if "last_push" not in st.session_state or datetime.now() - st.session_state.last_push > timedelta(minutes=5):
            push_line_msg(msg)
            st.session_state.last_push = datetime.now()

    # 燈號顯示區
    cl, cr = st.columns(2)
    with cl: st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴'*r_count}{'⚪'*(3-r_count)}</p></div>", unsafe_allow_html=True)
    with cr: st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢'*g_count}{'⚪'*(3-g_count)}</p></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # 三大看板：字體等大校正
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微台{target_code[4:]}全</p>", unsafe_allow_html=True)
    with m2:
        change = last['Close'] - prev['Close']
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    # 技術位階
    st.markdown("---")
    day_h, day_l = df['High'].max(), df['Low'].min()
    diff = day_h - day_l
    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")
else:
    st.warning("📊 戰情數據 3分K 重新同步中...")
