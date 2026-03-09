import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 環境穩定性校正：解決環境變數衝突
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")

# 自動刷新功能：每 30 秒強制更新一次點位
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 🎯 原始產品清單：保證這 5 項商品完整歸位，不跑掉
SYMBOL_MAP = {
    "加權指數": "^TWII",        # 台灣大盤點位
    "微台近全": "WTX=F",       # 台指期全天候合約
    "台積電": "2330.TW",       # 台股權值王
    "台積電 ADR": "TSM",       # 美股台積電憑證
    "ESG 永續 (00850)": "00850.TW" # ESG 永續 ETF
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 精準數據引擎：直接存取原始 JSON，解析 1 分鐘線序列
@st.cache_data(ttl=15)
def get_safe_data(symbol):
    try:
        # 使用 1d 範圍與 1m 間隔，確保點位精準對齊盤中價格
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        
        # 精確過濾數值：排除空值並抓取最新成交價，解決數據延遲問題
        closes = [x for x in indicators['close'] if x is not None]
        highs = [x for x in indicators['high'] if x is not None]
        lows = [x for x in indicators['low'] if x is not None]
        
        if not closes: 
            return None, None, None
            
        return float(closes[-1]), float(max(highs)), float(min(lows))
    except:
        return None, None, None

# 執行抓取
c, h, l = get_safe_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 戰情看板顯示：徹底移除所有噴錯語法
if c is not None:
    diff = h - l
    st.success(f"📈 {selected_label} 同步成功 (實時點位)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("即時價", f"{c:,.2f}")
    col2.metric("今日高", f"{h:,.2f}")
    col3.metric("今日低", f"{l:,.2f}")
    
    # 使用 Markdown 橫線替代會導致報錯的 st.divider()
    st.markdown("---")
    
    # 核心：關鍵點位計算 (0.618 / 0.382)
    p_zone = l + diff * 0.618
    s_zone = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{p_zone:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{s_zone:,.2f}**")
else:
    st.warning("⚠️ 數據同步中，請等待 30 秒自動刷新或檢查連線。")
