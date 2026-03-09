import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 穩定性環境校正：避開 Protobuf 衝突
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")

# 2. 強制 30 秒自動刷新
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 原始產品清單 (確保代碼正確對齊)
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "台積電": "2330.TW",
    "鴻海": "2317.TW",
    "ESG 永續 (00850)": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 3. 數據核心：直接抓取 Yahoo 底層 JSON，不再發生 JSONDecodeError
@st.cache_data(ttl=15)
def get_safe_data(symbol):
    try:
        # 使用 1d + 1m 確保點位精準對齊盤中價格
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        quote = result['indicators']['quote'][0]
        
        # 精確過濾數值
        closes = [x for x in quote['close'] if x is not None]
        highs = [x for x in quote['high'] if x is not None]
        lows = [x for x in quote['low'] if x is not None]
        
        if not closes: return None, None, None
            
        return float(closes[-1]), float(max(highs)), float(min(lows))
    except:
        return None, None, None

# 數據讀取
c, h, l = get_safe_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 4. 看板顯示 (移除所有噴錯語法)
if c is not None:
    diff = h - l
    st.success(f"📈 {selected_label} 連線成功")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("即時價", f"{c:,.2f}")
    col2.metric("今日高", f"{h:,.2f}")
    col3.metric("今日低", f"{l:,.2f}")
    
    # 用 markdown 替代 st.divider()，保證不報錯
    st.markdown("---")
    
    # 強哥核心：關鍵點位計算
    p_val = l + diff * 0.618
    s_val = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{p_val:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{s_val:,.2f}**")
else:
    st.warning("⚠️ 數據同步中，請等待 30 秒自動刷新...")
