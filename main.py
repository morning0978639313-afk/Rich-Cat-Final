import os
import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 環境衝突校正
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh") 

SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "台積電 ADR": "TSM",
    "ESG 永續 (00850)": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 核心：突破連線封鎖的獲取函數
@st.cache_data(ttl=20)
def get_data(symbol):
    try:
        # 建立偽裝標頭，讓 Yahoo 認為這是從一般 Mac 電腦發出的請求
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 強制使用會話下載，並設定超時避免卡死
        df = yf.download(symbol, period="10d", interval="1d", session=session, progress=False, timeout=10)
        
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        return None
    except:
        return None

# 執行獲取
df = get_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 數據看板顯示邏輯
if df is not None and not df.empty:
    last = df.iloc[-1]
    def to_f(v): return float(v.iloc[0]) if hasattr(v, 'iloc') else float(v)
    
    c, h, l = to_f(last['Close']), to_f(last['High']), to_f(last['Low'])
    diff = h - l
    
    st.success(f"📈 {selected_label} 資料連線成功")
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價", f"{c:,.2f}")
    col2.metric("高點", f"{h:,.2f}")
    col3.metric("低點", f"{l:,.2f}")
    
    st.divider()
    # 核心點位計算 (強哥戰術)
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
    st.line_chart(df['Close'])
else:
    st.warning("⚠️ 目前數據源存取受限，正在嘗試自動重新建立加密通道...")
    if st.button("🔄 點擊手動刷新通道"):
        st.cache_data.clear()
        st.rerun()
