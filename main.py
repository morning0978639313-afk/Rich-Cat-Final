import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 核心設定：解決環境衝突
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 穩定代碼清單
SYMBOL_MAP = {
    "台積電": "2330.TW",
    "鴻海": "2317.TW",
    "加權指數": "^TWII",
    "00850": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 核心：繞過套件封鎖，直接使用底層 API 抓取數據
@st.cache_data(ttl=20)
def get_live_data(symbol):
    try:
        # 使用 Yahoo 原始 Chart API，這在雲端環境最穩定
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=10d&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        # 解析 JSON 結構
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        indicators = result['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'Date': [datetime.fromtimestamp(t) for t in timestamps],
            'Close': indicators['close'],
            'High': indicators['high'],
            'Low': indicators['low']
        }).dropna()
        return df
    except:
        return None

# 執行資料抓取
df = get_live_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 顯示戰情看板
if df is not None and not df.empty:
    last = df.iloc[-1]
    c, h, l = float(last['Close']), float(last['High']), float(last['Low'])
    diff = h - l
    
    st.success(f"📈 {selected_label} 連線成功 (底層通道已開啟)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價", f"{c:,.2f}")
    col2.metric("高點", f"{h:,.2f}")
    col3.metric("低點", f"{l:,.2f}")
    
    st.divider()
    # 強哥核心：關鍵點位計算
    st.error(f"🚀 壓力區 (0.618)：**{l + diff * 0.618:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{l + diff * 0.382:,.2f}**")
    
    # 畫出走勢圖
    st.line_chart(df.set_index('Date')['Close'])
else:
    st.error("❌ 數據源連線受阻，請點擊右下角 Manage app 執行 Reboot 重啟通道。")
