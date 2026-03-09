import os
import streamlit as st
import pandas as pd
import pytz
import calendar
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (適配 v1.19.0)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") # 15秒超快同步

# CSS：解決問題 2 (商品名稱與數字等大 48px)
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; font-family: 'Courier New', Courier, monospace; }
    .label-text { font-size:20px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #111111; padding: 20px; border-radius: 15px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 2. 自動結算邏輯：日期 + 13:30 分判定
def get_war_room_contract():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    year, month = now.year, now.month
    c = calendar.monthcalendar(year, month)
    w3 = c[2][calendar.WEDNESDAY] if c[0][calendar.WEDNESDAY] != 0 else c[3][calendar.WEDNESDAY]
    cutoff = datetime(year, month, w3, 13, 30, tzinfo=tz)
    
    if now > cutoff:
        if month == 12: year, month = year + 1, 1
        else: month += 1
    return f"{year}{month:02d}"

target_code = get_war_room_contract()
tw_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{tw_time} | 🎯 監控合約：TX{target_code} (全時段)</p>", unsafe_allow_html=True)

# 3. 數據引擎：鎖定「全盤」成交量最大合約
@st.cache_data(ttl=10)
def fetch_full_session_data(code):
    try:
        dl = DataLoader()
        # 抓取期貨資料
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df.columns = [str(c).lower().strip() for c in df.columns]
            # 過濾當前主力月份
            df = df[df['contract_date'] == code].copy()
            
            # 欄位校正：FinMind max/min 轉為 High/Low
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            
            # 去重並轉換數值
            df = df.loc[:, ~df.columns.duplicated()].copy()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 【關鍵】：取最新日期中成交量最大的一筆 (即為「全盤/主力」合約)
            latest_date = df['date'].max()
            df_latest = df[df['date'] == latest_date].sort_values('Volume', ascending=False).head(1)
            
            # 抓取前一日資料計算漲跌
            df_prev = df[df['date'] < latest_date].tail(1)
            return pd.concat([df_prev, df_latest])
    except: pass
    return None

df = fetch_full_session_data(target_code)

# 4. 戰情室畫面呈現
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 漲跌計算：鎖定對齊「全盤」漲跌
    change = last['Close'] - df.iloc[0]['Close'] if len(df) > 1 else 0
    
    # 燈號區 (維持 3 顆佔位)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴' if change > 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢' if change < 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大看板：商品名稱、漲跌、即時價格
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微台{target_code[4:]}全</p>", unsafe_allow_html=True)
    with m2:
        # 紅漲綠跌
        color = "#FF4B4B" if change >= 0 else "#00D100"
        st.markdown("<p class='label-text'>📊 漲跌點數</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val' style='color:{color};'>{change:+.0f}</p>", unsafe_allow_html=True)
    with m3:
        # 點位精準鎖定 32k
        st.markdown("<p class='label-text'>💰 即時價格</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>{last['Close']:,.0f}</p>", unsafe_allow_html=True)

    st.markdown("---")
    # 強哥位階
    h, l = last['High'], last['Low']
    diff = h - l
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")

else:
    st.warning(f"📊 正在為您鎖定微台{target_code[4:]}全 數據，請稍候...")
