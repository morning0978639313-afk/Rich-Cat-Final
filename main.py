import os
import streamlit as st
import yfinance as yf
import pandas as pd
import pytz
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 環境衝突解決 (必須在最前)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

# 2. 頁面基礎設定
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh") # 30秒自動重整

SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "台積電 ADR": "TSM",
    "ESG 永續 (00850)": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 3. 核心數據獲取函數 (加強偽裝與穩定性)
@st.cache_data(ttl=30)
def get_data(symbol):
    try:
        # 下載最近 10 天，使用較穩定的 Ticker 物件
        tk = yf.Ticker(symbol)
        df = tk.history(period="10d", interval="1d", timeout=10)
        
        if df is not None and not df.empty:
            # 修正欄位結構 (移除 MultiIndex)
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

# 4. 戰情指標顯示
if df is not None and not df.empty:
    last = df.iloc[-1]
    
    # 數值保護轉換函數
    def to_f(v): return float(v.iloc[0]) if hasattr(v, 'iloc') else float(v)
    
    c = to_f(last['Close'])
    h = to_f(last['High'])
    l = to_f(last['Low'])
    diff = h - l
    
    st.success(f"📈 {selected_label} 連線成功")
    
    # 三欄看板
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價格", f"{c:,.2f}")
    col2.metric("本日高點", f"{h:,.2f}")
    col3.metric("本日低點", f"{l:,.2f}")
    
    st.divider()
    
    # 核心點位計算 (強哥戰術)
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")
    
    # 簡單折線圖
    st.line_chart(df['Close'])
else:
    # 提示與手動重連按鈕
    st.warning("⚠️ 目前數據源連線受阻，正在嘗試繞過防火牆...")
    if st.button("🔄 點擊強制刷新通道"):
        st.cache_data.clear()
        st.rerun()
