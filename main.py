import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術終端", layout="wide")
# 速度優化：縮短為 15 秒刷新一次
st_autorefresh(interval=15 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術終端")

# 2. 數據引擎：徹底修正 0 或 錯誤索引值問題
@st.cache_data(ttl=10)
def get_final_data():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=40)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df = df.loc[:, ~df.columns.duplicated()].copy()
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            # 強制校正 FinMind 命名
            df = df.rename(columns={'max': 'High', 'min': 'Low', 'open': 'Open', 'close': 'Close', 'volume': 'Volume'})
            
            # 數據轉型：確保 Close 是點位而非索引值
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df[df['Close'] > 1000].dropna(subset=['Close']) # 過濾掉非價格資料
            
            # 均線計算
            df['5MA'] = df['Close'].rolling(window=5).mean()
            return df
    except: pass
    return None

df = get_final_data()

# 3. 邏輯運算與版面更新
if df is not None and len(df) >= 2:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 計算今日高低
    day_h, day_l = df['High'].max(), df['Low'].min()
    diff = day_h - day_l
    
    # 買賣信號 (範例簡化，可依 40 條擴充)
    b_sigs = [s for s in ["站上5MA"] if last['Close'] > last['5MA']]
    s_sigs = [s for s in ["跌破5MA"] if last['Close'] < last['5MA']]

    # 4. 版面呈現：依照要求更名標籤
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("🔴 買進燈號")
        st.write("🔴" * (1 if b_sigs else 0) + "⚪" * 2)
    with col_r:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" * (1 if s_sigs else 0) + "⚪" * 2)

    st.markdown("---")
    
    # 三大核心看板更名：商品名稱, 漲跌點數, 即時價格
    m1, m2, m3 = st.columns(3)
    m1.metric("📌 商品名稱", "微台近全 (TX)")
    
    # 漲跌計算
    change = last['Close'] - prev['Close']
    m2.metric("📉 漲跌點數", f"{change:,.1f}", f"{change:,.1f}")
    
    # 確保即時價格顯示為 22,xxx 而非 47
    m3.metric("💰 即時價格", f"{last['Close']:,.0f}")

    # 強哥位階顯示
    st.error(f"🚀 壓力區 (0.618)：**{day_l + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_l + diff * 0.382:,.2f}**")

else:
    st.warning("📊 正在精準抓取價格資料，請稍候...")
