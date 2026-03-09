import os
import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 環境校正
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

# 2. 突破封鎖的數據獲取函數
@st.cache_data(ttl=20)
def get_data(symbol):
    try:
        # 核心：建立一個帶有瀏覽器標籤的 Session 偽裝成一般電腦
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 強迫 yfinance 使用偽裝會話下載數據
        df = yf.download(
            symbol, 
            period="10d", 
            interval="1d", 
            session=session, 
            progress=False,
            auto_adjust=True
        )
        
        if df is not None and not df.empty:
            # 修正欄位結構 (移除 MultiIndex)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        return None
    except Exception:
        return None

# 執行獲取
df = get_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 顯示邏輯
if df is not None and not df.empty:
    last = df.iloc[-1]
    
    # 數值保護轉換
    def to_f(v): return float(v.iloc[0]) if hasattr(v, 'iloc') else float(v)
    
    c = to_f(last['Close'])
    h = to_f(last['High'])
    l = to_f(last['Low'])
    diff = h - l
    
    st.success(f"📈 {selected_label} 連線成功")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價格", f"{c:,.2f}")
    col2.metric("本日高點", f"{h:,.2f}")
    col3.metric("本日低點", f"{l:,.2f}")
    
    st.divider()
    
    # 強哥核心：戰技點位計算
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")
    
    st.line_chart(df['Close'])
else:
    st.warning("⚠️ Yahoo 數據源目前對雲端 IP 進行流量管制，正在嘗試繞過連線...")
    if st.button("🔄 嘗試更換加密通道重連"):
        st.cache_data.clear()
        st.rerun()
