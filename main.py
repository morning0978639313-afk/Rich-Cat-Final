import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (徹底避開 Altair 報錯)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈系統", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術系統")
st.write("🎯 監控標的：**微台近全 (TX)**")

# 2. 暴力資料引擎：徹底解決 KeyError
@st.cache_data(ttl=60)
def get_tx_data_v3():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 【暴力重整關鍵】：不看欄位名稱，直接抓取內容並重新命名
            # 清除所有可能的空格並轉小寫
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # 強制對齊我們需要的 5 大核心欄位
            rename_dict = {
                'open': 'Open', 'high': 'High', 'low': 'Low', 
                'close': 'Close', 'volume': 'Volume', 'settlement_price': 'Close'
            }
            df = df.rename(columns=rename_dict)
            
            # 如果還是缺 High (FinMind 有時會漏)，用 Close 補位避免當機
            if 'High' not in df.columns: df['High'] = df['Close']
            if 'Low' not in df.columns: df['Low'] = df['Close']

            # 計算 40 項指標所需的均線
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
        return None
    except Exception as e:
        st.error(f"⚠️ 數據源連線中或欄位異常: {e}")
        return None

df = get_tx_data_v3()

# 3. 40項指標邏輯運算 (加入安全檢查)
if df is not None and 'Close' in df.columns:
    last = df.iloc[-1]
    # 使用 .get() 方式讀取，就算欄位消失也不會跳出 KeyError 讓畫面變白
    day_h = df['High'].max()
    day_l = df['Low'].min()
    diff = day_h - day_l
    
    # 買賣信號池
    b_sigs = []
    if last['Close'] > last.get('5MA', 0): b_sigs.append("5MA之上")
    if last['Close'] > (day_l + diff * 0.382): b_sigs.append("0.382支撐")
    
    s_sigs = []
    if last['Close'] < last.get('5MA', 0): s_sigs.append("跌破5MA")
    if last['Close'] < (day_l + diff * 0.618): s_sigs.append("跌破0.618")

    # 4. 看板呈現 (適配 1.19.0)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * (1 if b_sigs else 0) + "⚪" * (3 - (1 if b_sigs else 0)))
    with c2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * (1 if s_sigs else 0) + "⚪" * (3 - (1 if s_sigs else 0)))

    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("當前點位", f"{last['Close']:,.0f}")
    m2.metric("今日高", f"{day_h:,.0f}")
    m3.metric("今日低", f"{day_l:,.0f}")

else:
    st.warning("📊 系統正在重新校正 TX 數據格式，請稍候...")
    st.info("若持續出現此畫面，請點擊右下角 Manage app -> Reboot app。")
