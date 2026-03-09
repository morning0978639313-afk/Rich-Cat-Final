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

# 強制黑底白字 CSS，徹底解決配色錯誤
st.markdown("""
    <style>
    /* 強制全域黑底 */
    .stApp { background-color: #000000; }
    /* 看板背景設定 */
    .center-box { 
        text-align: center; 
        background-color: #111111; 
        padding: 25px; 
        border-radius: 15px; 
        border: 2px solid #333333;
    }
    /* 商品名稱與數字對齊鎖定 48px */
    .big-val { font-size:48px !important; font-weight: bold; color: #FFFFFF; }
    .label-text { font-size:22px; color: #AAAAAA; margin-bottom: -15px; }
    h1 { color: #FFFFFF !important; text-align: center; font-weight: bold; }
    p, span, div { color: #FFFFFF; }
    </style>
    """, unsafe_allow_html=True)

st.title("🐱 RICH CAT 戰情室")

# 2. 自動結算邏輯：日期 + 13:30 (結算後自動跳下個月)
def get_current_mxf_contract():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    y, m = now.year, now.month
    c = calendar.monthcalendar(y, m)
    w3 = [week[calendar.WEDNESDAY] for week in c if week[calendar.WEDNESDAY] != 0]
    s_day = w3[2] if c[0][calendar.WEDNESDAY] != 0 else w3[3]
    
    cutoff = datetime(y, m, s_day, 13, 30, tzinfo=tz)
    if now > cutoff:
        if m == 12: y, m = y + 1, 1
        else: m += 1
    return f"{y}{m:02d}"

target_m = get_current_mxf_contract()
tw_now = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center; color: #888;'>🕒 台北實時：{tw_now} | 🎯 監控合約：微小台 MXF{target_m}</p>", unsafe_allow_html=True)

# 3. 數據引擎：鎖定 微小台 (MXF) 全盤
@st.cache_data(ttl=10)
def fetch_mxf_clean_data(code):
    try:
        dl = DataLoader()
        # 抓取 微小台 (MXF)
        df = dl.taiwan_futures_daily(
            futures_id='MXF', 
            start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 鎖定月份合約
            df = df[df['contract_date'] == code].copy()
            if df.empty: return None

            # 暴力改名：解決 KeyError: 'High' 與 max/min 的命名衝突
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            df = df.loc[:, ~df.columns.duplicated()].copy()
            
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 抓取當日成交量最大者 (對齊「全盤」報價 32,013)
            latest_d = df['date'].max()
            df_now = df[df['date'] == latest_d].sort_values('Volume', ascending=False).head(1)
            df_prev = df[df['date'] < latest_d].tail(1)
            return pd.concat([df_prev, df_now])
    except: pass
    return None

df = fetch_mxf_clean_data(target_m)

# 4. UI 排版呈現
if df is not None and not df.empty:
    last = df.iloc[-1]
    # 漲跌計算
    change = last['Close'] - df.iloc[0]['Close'] if len(df) > 1 else 0
    
    # 燈號 (依據漲跌變動)
    r_on = 1 if change > 0 else 0
    g_on = 1 if change < 0 else 0

    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴' * r_on + '⚪' * (3-r_on)}</p></div>", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢' * g_on + '⚪' * (3-g_on)}</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標：商品、漲跌、價格 (對齊 48px)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"<div class='center-box'><p class='label-text'>📌 商品名稱</p><p class='big-val'>微小台{target_m[4:]}全</p></div>", unsafe_allow_html=True)
    with m2:
        # 漲必紅、跌必綠
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown(f"<div class='center-box'><p class='label-text'>📊 漲跌點數</p><p class='big-val' style='color:{color};'>{change:+.0f}</p></div>", unsafe_allow_html=True)
    with m3:
        # 即時價格鎖定 (對齊 32,013)
        st.markdown(f"<div class='center-box'><p class='label-text'>💰 即時價格</p><p class='big-val'>{last['Close']:,.0f}</p></div>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥關鍵位階判定
    h, l = last['High'], last['Low']
    diff = h - l
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
else:
    st.warning("📊 正在同步微小台全盤數據，請確認 API 連線或點擊 Reboot App。")
