import os
import streamlit as st
import pandas as pd
import pytz
import calendar
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (解決 Altair 報錯)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") 

# CSS：確保商品名稱與報價數字一樣大 (48px)
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; font-family: 'Courier New', Courier, monospace; }
    .label-text { font-size:22px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# 標題更正
st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 2. 自動結算邏輯：日期 + 13:30 判定
def get_active_mxf_code():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    year, month = now.year, now.month
    c = calendar.monthcalendar(year, month)
    # 取當月第三個星期三
    w3 = [week[calendar.WEDNESDAY] for week in c if week[calendar.WEDNESDAY] != 0]
    s_day = w3[2] if c[0][calendar.WEDNESDAY] != 0 else w3[3]
    
    # 結算時間點：當天 13:30
    cutoff = datetime(year, month, s_day, 13, 30, tzinfo=tz)
    if now > cutoff:
        if month == 12: year, month = year + 1, 1
        else: month += 1
    return f"{year}{month:02d}"

target_code = get_active_mxf_code()
tw_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{tw_time} | 🎯 監控合約：微小台 (MXF) {target_code}</p>", unsafe_allow_html=True)

# 3. 數據引擎：鎖定微小台 (MXF) 全盤資料
@st.cache_data(ttl=10)
def fetch_mxf_fixed_data(code):
    try:
        dl = DataLoader()
        # 抓取 微小台 (MXF)
        df = dl.taiwan_futures_daily(
            futures_id='MXF', 
            start_date=(datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 鎖定特定合約
            df = df[df['contract_date'] == code].copy()
            if df.empty: return None

            # 暴力更名：解決 KeyError: 'High' 惡疾
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            
            # 移除重複與數值化
            df = df.loc[:, ~df.columns.duplicated()].copy()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 抓取「全盤」成交量最大的一筆資料
            latest_date = df['date'].max()
            df_now = df[df['date'] == latest_date].sort_values('Volume', ascending=False).head(1)
            df_prev = df[df['date'] < latest_date].tail(1)
            
            return pd.concat([df_prev, df_now])
    except: pass
    return None

df = fetch_mxf_fixed_data(target_code)

# 4. 戰情室 UI 呈現
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 漲跌計算
    change = last['Close'] - df.iloc[0]['Close'] if len(df) > 1 else 0
    
    # 燈號
    r_on = 1 if change > 0 else 0
    g_on = 1 if change < 0 else 0

    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴' * r_on + '⚪' * (3-r_on)}</p></div>", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢' * g_on + '⚪' * (3-g_on)}</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標：商品名稱、漲跌、價格
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微小台{target_code[4:]}全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        # 正確點位鎖定 32k
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥關鍵位階
    h, l = last['High'], last['Low']
    diff = h - l
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")

else:
    st.warning(f"📊 數據源精準鎖定中... 請檢查微小台{target_code}全 的開盤狀態，並點擊 Reboot App。")
