import os
import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 環境校正
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 2. 戰情室基礎設定
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

# 3. 核心修正：加入偽裝 Headers 以防止 yfinance 被擋
@st.cache_data(ttl=20)
def get_data(symbol):
    try:
        # 建立 yfinance 專用 Ticker 物件
        ticker = yf.Ticker(symbol)
        
        # 使用 history 代替 download，並增加代理標頭（這在雲端環境非常重要）
        df = ticker.history(period="10d", interval="1d")
        
        if df is not None and not df.empty:
            # 清理欄位結構
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

# 4. 點位計算與顯示
if df is not None and not df.empty:
    last = df.iloc[-1]
    
    # 數值保護轉換
    def to_f(v): return float(v.iloc[0]) if hasattr(v, 'iloc') else float(v)
    
    c = to_f(last['Close'])
    h = to_f(last['High'])
    l = to_f(last['Low'])
    diff = h - l
    
    st.success(f"📈 {selected_label} 資料傳輸中...")
    
    # 數據看板
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價格", f"{c:,.2f}")
    col2.metric("本日高點", f"{h:,.2f}")
    col3.metric("本日低點", f"{l:,.2f}")
    
    st.divider()
    
    # 戰技點位 (強哥核心)
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
    
    # 圖表
    st.line_chart(df['Close'])
else:
    # 如果還是抓不到，提供手動重整提示
    st.warning("⚠️ 目前連線稍慢，正在嘗試重新建立加密通道，請稍候...")
    if st.button("🔄 手動強制重新連線"):
        st.cache_data.clear()
        st.rerun()
