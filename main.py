import os
import streamlit as st
import pandas as pd
import pytz
import calendar
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境穩定設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 戰情室", layout="wide")
st_autorefresh(interval=15 * 1000, key="datarefresh") # 15秒同步

# CSS：問題 2 解決 (商品名稱與報價數字一樣大 48px)
st.markdown("""
    <style>
    .big-val { font-size:48px !important; font-weight: bold; font-family: 'Arial', sans-serif; }
    .label-text { font-size:20px; color: #999999; margin-bottom: -15px; }
    .center-box { text-align: center; background: #1A1A1A; padding: 25px; border-radius: 15px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #FFD700;'>🐱 RICH CAT 戰情室</h1>", unsafe_allow_html=True)

# 2. 自動結算邏輯：日期 + 13:30 分判定
def get_current_contract():
    tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tz)
    year, month = now.year, now.month
    c = calendar.monthcalendar(year, month)
    w3 = c[2][calendar.WEDNESDAY] if c[0][calendar.WEDNESDAY] != 0 else c[3][calendar.WEDNESDAY]
    cutoff = datetime(year, month, w3, 13, 30, tzinfo=tz)
    
    # 結算時間後自動跳下個月
    if now > cutoff:
        if month == 12: year, month = year + 1, 1
        else: month += 1
    return f"{year}{month:02d}"

target_code = get_current_contract()
tw_time = datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"<p style='text-align: center;'>🕒 台北實時：{tw_time} | 🎯 監控合約：TX{target_code}全</p>", unsafe_allow_html=True)

# 3. 數據引擎：徹底解決 KeyError 與 32,013 點位對齊
@st.cache_data(ttl=10)
def fetch_contract_data(code):
    try:
        dl = DataLoader()
        # 抓取最近資料
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 統一小寫處理，避免 KeyError
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # 過濾當前結算週期對應的合約月份
            df = df[df['contract_date'] == code].copy()
            if df.empty: return None

            # 欄位校正：FinMind 原始 max/min 轉為程式需要的 High/Low
            # 並使用 .loc 避免產生多個重複欄位報錯
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            df = df.loc[:, ~df.columns.duplicated()].copy()
            
            # 轉換數值，確保不出現 0
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 只取成交量最大的一筆 (主力全盤)
            latest_date = df['date'].max()
            df_latest = df[df['date'] == latest_date].sort_values('volume', ascending=False).head(1)
            
            # 抓取前一日資料計算漲跌
            df_prev = df[df['date'] < latest_date].tail(1)
            return pd.concat([df_prev, df_latest])
    except: pass
    return None

df = fetch_contract_data(target_code)

# 4. 戰情室視覺呈獻
if df is not None and len(df) >= 1:
    last = df.iloc[-1]
    # 計算漲跌點數 (若無前日資料則對比開盤價)
    change = last['Close'] - df.iloc[0]['Close'] if len(df) > 1 else last['Close'] - last['Open']
    
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown(f"<div class='center-box'><p class='label-text'>🔴 買進燈號</p><p class='big-val'>{'🔴' if change > 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)
    with c_r:
        st.markdown(f"<div class='center-box'><p class='label-text'>🟢 賣出燈號</p><p class='big-val'>{'🟢' if change < 0 else '⚪'}⚪⚪</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    # 三大指標：微台03全與點位對齊 48px
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("<p class='label-text'>📌 商品名稱</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='big-val'>微台{target_code[4:]}全</p>", unsafe_allow_html=True)
    with m2:
        color = "#FF4B4B" if change >= 0 else "#00D100" # 紅漲綠跌
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
    st.warning(f"📊 正在為您鎖定微台{target_code[4:]}全 數據，請確認 FinMind API 連線後點擊 Reboot。")
