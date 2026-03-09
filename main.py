import os
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 核心穩定設定與 30 秒戰情刷新
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 強哥戰情室", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

# 🎯 策略報告指定 5 大商品 (FinMind Code)
SYMBOL_MAP = {
    "加權指數": "TAIWAN_STOCK_INDEX",
    "微台近全": "TX",
    "台積電": "2330",
    "台積電 ADR": "TSM",
    "ESG 永續 (00850)",
    "0052"
}

st.title("🐱 RICH CAT 戰術指揮中心")
selected_label = st.selectbox("🎯 選擇作戰標的", list(SYMBOL_MAP.keys()))

# 2. 數據獲取 (徹底斷開 Yahoo)
@st.cache_data(ttl=60)
def get_strategy_data(stock_id):
    try:
        dl = DataLoader()
        # 抓取近 10 日數據以計算波段高低點 
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        if stock_id == "TAIWAN_STOCK_INDEX":
            df = dl.taiwan_stock_index_daily(stock_id=stock_id, start_date=start_date)
        else:
            df = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date)
        
        if df is not None and not df.empty:
            df = df.rename(columns={'close': 'Close', 'high': 'High', 'low': 'Low', 'open': 'Open', 'date': 'Date'})
            return df
        return None
    except:
        return None

df = get_strategy_data(SYMBOL_MAP[selected_label])

# 3. 戰技指標計算 [cite: 4, 5, 104]
if df is not None and not df.empty:
    last = df.iloc[-1]
    c, h, l, o = float(last['Close']), float(last['High']), float(last['Low']), float(last['Open'])
    diff = h - l
    
    # A. 黃金切割率位階 (波浪理論核心) [cite: 4, 5]
    p_618 = l + diff * 0.618  # 強力壓制/轉折位
    p_382 = l + diff * 0.382  # 強弱分水嶺/支撐位
    
    # B. 關鍵 K 棒目標價公式 
    # 公式：(收盤 - 開盤) * 0.618 + 開盤
    target_price = (c - o) * 0.618 + o
    
    # 4. 戰情看板介面
    st.success(f"✅ {selected_label} 通訊導通 | 台北時間: {datetime.now(pytz.timezone('Asia/Taipei')).strftime('%H:%M:%S')}")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("實時成交價", f"{c:,.2f}")
    m2.metric("今日最高點", f"{h:,.2f}")
    m3.metric("今日最低點", f"{l:,.2f}")
    
    st.markdown("---")
    
    # 5. 策略警示與訊號判斷
    left, right = st.columns(2)
    
    with left:
        st.subheader("🛡️ 波浪位階 (黃金切割)")
        # 報告準則：回歸不破 0.382 代表強，跌破 0.618 代表趨勢破壞 
        if c > p_382:
            st.write("📈 **多方強勢區**：回測不破 0.382，隨時再噴 ")
        elif c < p_618:
            st.write("📉 **空方破壞區**：跌破 0.618，上升段已瓦解 ")
        
        st.error(f"🔴 壓制區 (0.618)：{p_618:,.2f}")
        st.info(f"🔵 支撐區 (0.382)：{p_382:,.2f}")

    with right:
        st.subheader("🚀 關鍵 K 棒預測")
        st.warning(f"🎯 戰術目標價：{target_price:,.2f}")
        st.write("> *公式依據：(收盤-開盤) * 0.618 + 開盤 *")

    # 6. 主力攻擊密碼偵測 (三兵訊號判斷邏輯示意) 
    st.markdown("---")
    st.subheader("⚔️ 主力攻擊密碼")
    if c > o:
        st.write("🔥 **疑似紅三兵發動**：若連續三根實體紅棒，代表主力大舉進場 [cite: 87, 91]")
    else:
        st.write("❄️ **疑似黑三兵下殺**：若連續三根實體黑棒，代表空方主力倒貨 [cite: 88, 91]")

else:
    st.error("❌ 數據源連線中，請點擊下方 Manage app 並 Reboot app。")
