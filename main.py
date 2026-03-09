import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime

# 1. 核心設定：避開所有可能衝突的環境變數
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")

# 穩定代碼清單
SYMBOL_MAP = {
    "台積電": "2330.TW",
    "鴻海": "2317.TW",
    "加權指數": "^TWII",
    "00850": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 核心數據獲取：直接使用底層 API，繞過 yfinance 套件
@st.cache_data(ttl=20)
def get_live_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        
        # 只抓取最新的價格數據
        c = indicators['close'][-1]
        h = indicators['high'][-1]
        l = indicators['low'][-1]
        return c, h, l
    except:
        return None, None, None

# 執行抓取
c, h, l = get_live_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 顯示戰情看板 (使用 st.metric，這絕對不會觸發 altair 錯誤)
if c is not None:
    diff = h - l
    st.success(f"📈 {selected_label} 連線成功")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價", f"{c:,.2f}")
    col2.metric("本日高點", f"{h:,.2f}")
    col3.metric("本日低點", f"{l:,.2f}")
    
    st.divider()
    # 強哥核心：關鍵點位計算
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")
    
    # 提醒按鈕
    if st.button("🔄 手動刷新數據"):
        st.cache_data.clear()
        st.rerun()
else:
    st.error("❌ 數據源連線受阻，請點擊下方 Manage app 並選擇 Reboot 重啟通道。")
