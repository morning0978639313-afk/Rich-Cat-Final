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

# CSS：確保商品名稱與報價數字一樣大 (48px)
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; }
    .label-text { font-size:22px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 2. 自動結算邏輯：鎖定 微小台 (MXF) 202603
def get_mxf_contract():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    year, month = now.year, now.month
    c = calendar.monthcalendar(year, month)
    w3 = [week[calendar.WEDNESDAY] for week in c if week[calendar.WEDNESDAY] != 0]
    settlement_day = w3[2] if c[0][calendar.WEDNESDAY] != 0 else w3[3]
    
    # 結算日 13:30 分界點
    cutoff = datetime(year, month, settlement_day, 13, 30, tzinfo=tz)
    if now > cutoff:
        if month == 12: year, month = year + 1, 1
        else: month += 1
    return f"{year}{month:02d}"

target_code = get_mxf_contract()
tw_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{tw_time} | 🎯 監控合約：微小台 (MXF){target_code}</p>", unsafe_allow_html=True)

# 3. 數據引擎：鎖定 微小台 (MXF) 202603 - 全
@st.cache_data(ttl=10)
def fetch_mxf_data(code):
    try:
        dl = DataLoader()
        # 抓取 微小台 (MXF) 數據
        df = dl.taiwan_futures_daily(
            futures_id='MXF', 
            start_date=(datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 鎖定特定合約日期 (例如 202603)
            df = df[df['contract_date'] == code].copy()
            if df.empty: return None

            # 暴力重命名欄位，徹底解決 KeyError: 'High'
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            
            # 去除重複欄位並數值化
            df = df.loc[:, ~df.columns.duplicated()].copy()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 只取最新日期中成交量最大的一筆 (全盤合約)
            latest_date = df['date'].max()
            df_now = df[df['date'] == latest_date].sort_values('Volume', ascending=False).head(1)
            df_prev = df[df['date'] < latest_date].tail(1)
            
            return pd.concat([df_prev, df_now])
    except: pass
    return None

df = fetch_mxf_data(target_code)

# 4. 戰情室呈現
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 漲跌點數
    change = last['Close'] - df.iloc[0]['Close'] if len(df) > 1 else 0
    
    # 燈號 (🔴 > 0, 🟢 < 0)
    r_light = "🔴" if change > 0 else "⚪"
    g_light = "🟢" if change < 0 else "⚪"

    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{r_light}⚪⚪</p></div>", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{g_light}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標看板
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微小台{target_code[4:]}全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥關鍵位階
    h, l = last['High'], last['Low']
    diff = h - l
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")

else:
    st.warning(f"📊 正在精準鎖定 微小台{target_code}全 數據，請稍候並點擊 Reboot App...")
