import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 核心設定與自動刷新
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 使用台股最穩定的代碼格式
SYMBOL_MAP = {
    "台積電": "2330",
    "00850": "00850",
    "鴻海": "2317"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 終極數據獲取：使用最穩定的 Web API 繞過所有套件衝突
@st.cache_data(ttl=20)
def get_safe_data(stock_id):
    try:
        # 抓取 Yahoo Finance 的 Web API 原始數據，避開 yfinance 套件的 Bug
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock_id}.TW?range=10d&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # 解析數據
        result = data['chart']['result'][0]
        dates = [datetime.fromtimestamp(t) for t in result['timestamp']]
        quote = result['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'Date': dates,
            'Close': quote['close'],
            'High': quote['high'],
            'Low': quote['low']
        })
        return df
    except:
        return None

# 執行獲取
df = get_safe_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 顯示邏輯
if df is not None and not df.empty:
    last = df.iloc[-1]
    c, h, l = float(last['Close']), float(last['High']), float(last['Low'])
    diff = h - l
    
    st.success(f"✅ {selected_label} 數據傳輸中...")
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價", f"{c:,.2f}")
    col2.metric("高點", f"{h:,.2f}")
    col3.metric("低點", f"{l:,.2f}")
    
    st.divider()
    # 強哥核心：戰技點位計算
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
    
    # 簡單圖表顯示
    st.line_chart(df.set_index('Date')['Close'])
else:
    st.error("❌ 目前數據通道維護中，請點擊 Manage app 執行 Reboot。")
