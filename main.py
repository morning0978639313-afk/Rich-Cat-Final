import os
import streamlit as st
import pandas as pd
import pytz
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定：強制開啟 30 秒自動刷新
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=30 * 1000, key="datarefresh") 

# 2. 嚴格鎖定商品清單 (不再跑掉)
SYMBOL_MAP = {
    "加權指數": "^TWII",
    "微台近全": "WTX=F",
    "台積電": "2330.TW",
    "00850 (ESG永續)": "00850.TW",
    "0052 (科技)": "0052.TW"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 3. 數據核心：使用 1m (分鐘級) 數據流繞過 Yahoo 封鎖與延遲
@st.cache_data(ttl=15)
def get_verified_data(symbol):
    try:
        # 強制獲取今日實時點位 (解決 33,599 vs 31,997 的問題)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        quote = result['indicators']['quote'][0]
        
        # 精確清洗數據：移除空值並抓取最後一個交易價格
        cl = [x for x in quote['close'] if x is not None]
        hi = [x for x in quote['high'] if x is not None]
        lo = [x for x in quote['low'] if x is not None]
        
        if not cl: return None, None, None
            
        return float(cl[-1]), float(max(hi)), float(min(lo))
    except:
        return None, None, None

# 執行讀取
c, h, l = get_verified_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 4. 戰情看板 (移除所有可能崩潰的語法)
if c is not None:
    diff = h - l
    st.success(f"📈 {selected_label} 連線成功 (實時點位)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("即時價", f"{c:,.2f}")
    col2.metric("今日高", f"{h:,.2f}")
    col3.metric("今日低", f"{l:,.2f}")
    
    # 移除 st.divider() 以防報錯，改用 Markdown
    st.markdown("---")
    
    # 核心點位計算
    p_val = l + diff * 0.618
    s_val = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{p_val:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{s_val:,.2f}**")
else:
    st.warning("⚠️ 數據源校正中，請等待 30 秒自動刷新...")
