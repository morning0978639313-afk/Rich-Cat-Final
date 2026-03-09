import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定 (避開 Altair 繪圖地雷)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈系統", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術系統")
st.write("🎯 標的：**微台近全 (TX)**")

# 2. 暴力資料引擎 V4：解決重複欄位與名稱衝突
@st.cache_data(ttl=60)
def get_tx_data_final():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 【關鍵修正 1】：強制移除重複的欄位名稱，解決 Multiple Columns 報錯
            df = df.loc[:, ~df.columns.duplicated()]
            
            # 【關鍵修正 2】：統一轉小寫並去空白，確保對齊基礎欄位
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # 建立對齊映射 (包含結算價 settlement_price 作為備援)
            rename_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume', 'settlement_price': 'Close'}
            df = df.rename(columns=rename_map)
            
            # 再次去重，防止改名後與舊名稱衝突
            df = df.loc[:, ~df.columns.duplicated()]

            # 均線計算 (使用 .copy() 確保資料獨立性)
            df = df.copy()
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            return df
        return None
    except Exception as e:
        st.error(f"⚠️ 數據讀取中: {e}")
        return None

df = get_tx_data_final()

# 3. 40項指標運算 (加入防禦性讀取)
if df is not None and 'Close' in df.columns:
    last = df.iloc[-1]
    # 使用 .get 避開 KeyError
    day_h = df['High'].max() if 'High' in df.columns else last['Close']
    day_l = df['Low'].min() if 'Low' in df.columns else last['Close']
    diff = day_h - day_l
    
    # 範例買進信號池 (🔴)
    b_sigs = []
    if last['Close'] > last.get('5MA', 0): b_sigs.append("5MA之上")
    if last['Close'] > (day_l + diff * 0.382): b_sigs.append("0.382位階")
    
    # 範例賣出信號池 (🟢)
    s_sigs = []
    if last['Close'] < last.get('5MA', 0): s_sigs.append("跌破5MA")
    if last['Close'] < (day_l + diff * 0.618): s_sigs.append("跌破0.618位階")

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
    m1.metric("當前價", f"{last['Close']:,.0f}")
    m2.metric("5MA位階", f"{last.get('5MA', 0):,.1f}")
    m3.metric("最新音量", f"{int(last.get('Volume', 0))}")
else:
    st.warning("📊 數據重新格式化中，請稍候...")
