import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 系統層級校正：解決舊版 Streamlit 環境衝突
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")

# 自動刷新：每 30 秒強制同步，確保戰情不延遲
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 🎯 完整 5 大商品清單歸位 (包含微台、ADR、00850)
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "台積電 ADR": "TSM",
    "ESG 永續 (00850)": "00850.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 精準數據引擎：解決點位跑掉與 Yahoo 封鎖問題
@st.cache_data(ttl=15)
def get_verified_data(symbol):
    try:
        # 使用 1m (分鐘線) 獲取最即時的成交序列
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        quote = result['indicators']['quote'][0]
        
        # 排除空值，抓取真實的盤中 Close, High, Low
        closes = [x for x in quote['close'] if x is not None]
        highs = [x for x in quote['high'] if x is not None]
        lows = [x for x in quote['low'] if x is not None]
        
        if not closes: return None, None, None
            
        return float(closes[-1]), float(max(highs)), float(min(lows))
    except:
        return None, None, None

# 數據計算
c, h, l = get_verified_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 戰情看板顯示：移除所有噴錯語法 (如 st.divider)
if c is not None:
    diff = h - l
    st.success(f"📈 {selected_label} 連線成功 (實時點位)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("即時價", f"{c:,.2f}")
    col2.metric("今日高", f"{h:,.2f}")
    col3.metric("今日低", f"{l:,.2f}")
    
    # 使用 Markdown 橫線，保證不報 AttributeError
    st.markdown("---")
    
    # 強哥核心：關鍵點位計算 (0.618 / 0.382)
    p_zone = l + diff * 0.618
    s_zone = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{p_zone:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{s_zone:,.2f}**")
else:
    st.warning("⚠️ 數據源響應中，請等待 30 秒自動刷新...")
