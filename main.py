import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 核心功能：30秒自動刷新，確保數據即時
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 指定你要求的四檔標的 (修正代碼確保抓取最即時數據)
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電 ADR": "TSM",
    "台積電": "2330.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 精準數據獲取：使用 1m 分鐘級數據繞過延遲
@st.cache_data(ttl=15)
def get_precise_data(symbol):
    try:
        # 使用 range=1d & interval=1m 抓取當日最細緻數據
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        meta = result['meta']
        
        # 優先從 meta 抓取當前市場價格 (Regular Market Price)
        c = meta.get('regularMarketPrice')
        h = meta.get('dayHigh')
        l = meta.get('dayLow')
        
        # 備援機制：如果 meta 沒給，從序列中找最後一個有效值
        if c is None:
            quote = result['indicators']['quote'][0]
            # 過濾掉 None 值
            valid_closes = [v for v in quote['close'] if v is not None]
            valid_highs = [v for v in quote['high'] if v is not None]
            valid_lows = [v for v in quote['low'] if v is not None]
            c = valid_closes[-1]
            h = max(valid_highs)
            l = min(valid_lows)
            
        return float(c), float(h), float(l)
    except Exception:
        return None, None, None

# 執行獲取
c, h, l = get_precise_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 顯示戰情看板
if c is not None:
    diff = h - l
    st.success(f"📈 {selected_label} 同步成功")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("即時價", f"{c:,.2f}")
    col2.metric("今日高", f"{h:,.2f}")
    col3.metric("今日低", f"{l:,.2f}")
    
    st.divider()
    
    # 強哥核心：關鍵點位計算 (0.618 / 0.382)
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")
    
    # 底部提醒
    st.caption(f"數據更新頻率：30秒 | 標的代碼：{SYMBOL_MAP[selected_label]}")
else:
    st.error("❌ 數據同步中，Yahoo 伺服器回應緩慢，請稍候或點擊下方重試。")
    if st.button("🔄 手動同步"):
        st.cache_data.clear()
        st.rerun()
