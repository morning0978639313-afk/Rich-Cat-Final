import os
import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 核心設定
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

# 2. 強化版數據獲取：加入 Session 偽裝
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        # 建立一個偽裝成瀏覽器的連線會話
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 使用 session 進行下載
        df = yf.download(symbol, period="10d", interval="1d", session=session, progress=False)
        
        if df is not None and not df.empty:
            # 處理 MultiIndex 欄位
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        return None
    except Exception as e:
        return None

# 執行獲取
df = get_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 顯示邏輯
if df is not None and not df.empty:
    last = df.iloc[-1]
    
    # 數值保護
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
    
    # 關鍵點位
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
    
    st.line_chart(df['Close'])
else:
    st.warning("⚠️ Yahoo 數據源目前對雲端 IP 進行流量管制。")
    st.info("💡 建議：點擊下方按鈕強制清除快取並重連。若多次失敗，可能是 Yahoo 暫時封鎖了 Streamlit 伺服器區域。")
    if st.button("🔄 嘗試更換加密通道重連"):
        st.cache_data.clear()
        st.rerun()
