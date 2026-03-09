import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 基礎設定：解決環境衝突並開啟 30 秒自動刷新
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 穩定標的清單
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "鴻海": "2317.TW",
    "ESG 永續 (00850)": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 核心：高頻數據抓取引擎
@st.cache_data(ttl=10)
def get_live_data(symbol):
    try:
        # 使用 1d 範圍與 1m 間隔，這能繞過 Yahoo 的緩存延遲數據
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        
        # 精準取值：排除空值並抓取最後一個交易價格
        closes = [x for x in indicators['close'] if x is not None]
        highs = [x for x in indicators['high'] if x is not None]
        lows = [x for x in indicators['low'] if x is not None]
        
        if not closes:
            return None, None, None
            
        c = closes[-1]
        h = max(highs) if highs else c
        l = min(lows) if lows else c
        
        return float(c), float(h), float(l)
    except:
        return None, None, None

# 執行抓取
c, h, l = get_live_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 戰情看板顯示
if c is not None:
    diff = h - l
    st.success(f"📈 {selected_label} 同步成功 (實時點位)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("即時價", f"{c:,.2f}")
    col2.metric("今日高", f"{h:,.2f}")
    col3.metric("今日低", f"{l:,.2f}")
    
    st.divider()
    
    # 強哥核心：關鍵點位計算
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")
else:
    st.warning("⚠️ 數據源響應緩慢，請耐心等待 30 秒自動刷新...")
