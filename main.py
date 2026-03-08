import os
import subprocess
import sys

# 1. 環境衝突解決方案
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# 2. 戰情室基礎設定 (優化手機顯示)
st.set_page_config(
    page_title="RICH CAT 終極戰情室", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 30秒自動刷新畫面
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 3. 定義追蹤標的
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "台積電 ADR": "TSM",
    "ESG 永續 (00850)": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

@st.cache_data(ttl=20)
def get_data(symbol):
    try:
        # 下載最近 10 天數據
        df = yf.download(symbol, period="10d", interval="1d", progress=False)
        if df is not None and not df.empty:
            # 處理 MultiIndex 欄位問題
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        return None
    except Exception as e:
        return None

# 執行資料獲取
df = get_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

st.write(f"🕒 台北實時：`{current_time}`")

# 4. 點位計算與顯示
if df is not None and not df.empty:
    last = df.iloc[-1]
    
    # 數值轉換確保計算正確
    def to_f(v): 
        return float(v.iloc[0]) if isinstance(v, pd.Series) else float(v)
    
    c = to_f(last['Close'])
    h = to_f(last['High'])
    l = to_f(last['Low'])
    diff = h - l
    
    st.success(f"✅ {selected_label} 連線成功")
    
    # 手機版建議使用 columns
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價", f"{c:,.2f}")
    col2.metric("最高", f"{h:,.2f}")
    col3.metric("最低", f"{l:,.2f}")
    
    st.divider()
    
    # 關鍵戰鬥點位
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：{pressure:,.2f}")
    st.info(f"🛡️ 支撐區 (0.382)：{support:,.2f}")
    
    # 簡單圖表輔助
    st.line_chart(df['Close'])
else:
    st.error("❌ 獲取資料失敗，請檢查網路或標的代碼。")
