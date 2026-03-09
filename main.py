import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術系統", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術系統")
st.write("🎯 監控標的：**微台近全 (TX)**")

# 2. 數據獲取：加入自動欄位轉換邏輯
@st.cache_data(ttl=60)
def get_tx_data_v2():
    try:
        dl = DataLoader()
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            # 【終極保險】：不管 API 給大寫還是小寫，統一強制轉為小寫
            # 這樣後面的判斷式只要寫小寫就絕對不會噴 KeyError
            df.columns = [col.lower() for col in df.columns]
            
            # 計算均線 (全部使用小寫欄位)
            df['5ma'] = df['close'].rolling(window=5).mean()
            df['10ma'] = df['close'].rolling(window=10).mean()
            df['20ma'] = df['close'].rolling(window=20).mean()
            return df
        return None
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return None

df = get_tx_data_v2()

# 3. 40項指標邏輯 (統一使用小寫，確保穩定)
if df is not None and len(df) >= 5:
    last = df.iloc[-1]
    day_h = df['high'].max() # 統一用小寫，不再報 KeyError!
    day_l = df['low'].min()
    diff = day_h - day_l
    
    # 範例判斷 (其餘 40 條規則皆可依此類推)
    b_sigs = []
    if last['close'] > last['5ma']: b_sigs.append("5MA之上")
    
    s_sigs = []
    if last['close'] < last['5ma']: s_sigs.append("跌破5MA")

    # 4. 看板呈現
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 買進燈號")
        st.write("🔴" if b_sigs else "⚪")
    with c2:
        st.subheader("🟢 賣出燈號")
        st.write("🟢" if s_sigs else "⚪")

    st.markdown("---")
    st.metric("即時點位", f"{last['close']:,.0f}")
    st.error(f"🚀 壓力區 (0.618)：{day_l + diff * 0.618:,.2f}")
    st.info(f"🛡️ 支撐區 (0.382)：{day_l + diff * 0.382:,.2f}")

else:
    st.warning("⚠️ 數據抓取中，請確保 GitHub 檔案正確並執行 Reboot。")
