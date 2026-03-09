import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 終極戰情室", layout="centered")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

# 穩定台股代碼清單
SYMBOL_MAP = {
    "台積電": "2330",
    "鴻海": "2317",
    "00850": "00850",
    "加權指數": "TAIWAN_STOCK_INDEX"
}

st.title("🐱 RICH CAT 終極戰情室")
selected_label = st.selectbox("🎯 切換追蹤商品", list(SYMBOL_MAP.keys()))

# 2. 核心數據獲取：使用 FinMind API (不需 Key)
@st.cache_data(ttl=60)
def get_finmind_data(stock_id):
    try:
        dl = DataLoader()
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        
        # 指數與個股判斷
        if stock_id == "TAIWAN_STOCK_INDEX":
            df = dl.taiwan_stock_index_daily(stock_id=stock_id, start_date=start_date)
        else:
            df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
            
        if df is not None and not df.empty:
            # 統一欄位名稱
            df = df.rename(columns={'close': 'Close', 'high': 'High', 'low': 'Low', 'date': 'Date'})
            return df
        return None
    except:
        return None

# 執行抓取
df = get_finmind_data(SYMBOL_MAP[selected_label])
tz = pytz.timezone('Asia/Taipei')
st.write(f"🕒 台北實時：`{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}`")

# 3. 戰情看板顯示 (使用最基礎、不噴錯的指令)
if df is not None and not df.empty:
    last = df.iloc[-1]
    c, h, l = float(last['Close']), float(last['High']), float(last['Low'])
    diff = h - l
    
    st.success(f"✅ {selected_label} 數據已成功同步")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("即時價", f"{c:,.2f}")
    col2.metric("今日高", f"{h:,.2f}")
    col3.metric("今日低", f"{l:,.2f}")
    
    # 畫出水平線 (替代 st.divider)
    st.markdown("---")
    
    # 強哥核心：關鍵點位計算
    pressure = l + diff * 0.618
    support = l + diff * 0.382
    
    st.error(f"🚀 壓力區 (0.618)：**{pressure:,.2f}**")
    st.info(f"🛡️ 支撐區 (0.382)：**{support:,.2f}**")
else:
    st.warning("⚠️ 數據源載入中，請耐心等待或確認 GitHub 零件已裝齊。")
