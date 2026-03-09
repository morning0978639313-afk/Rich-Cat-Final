import os
import streamlit as st
import pandas as pd
import pytz
import numpy as np
from datetime import datetime, timedelta
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh

# 1. 系統環境校正 (適配 v1.19.0)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
st.set_page_config(page_title="RICH CAT 紅綠燈戰術系統", layout="wide")
st_autorefresh(interval=60 * 1000, key="datarefresh") 

st.title("🐱 RICH CAT 紅綠燈戰術系統")
st.write("🎯 監控標的：**微台近全 (TX)** | 基準：**3分K邏輯**")

# 2. 數據獲取引擎：由 FinMind 提供精準台股數據
@st.cache_data(ttl=60)
def get_clean_data():
    try:
        dl = DataLoader()
        # 抓取最近資料以計算 5/10/20MA
        df = dl.taiwan_futures_daily(
            futures_id='TX', 
            start_date=(datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
        )
        if df is not None and not df.empty:
            df = df.rename(columns={'close': 'Close', 'high': 'High', 'low': 'Low', 'open': 'Open', 'volume': 'Volume'})
            # 均線系統校正
            df['5MA'] = df['Close'].rolling(window=5).mean()
            df['10MA'] = df['Close'].rolling(window=10).mean()
            df['20MA'] = df['Close'].rolling(window=20).mean()
            df['90MA'] = df['Close'].rolling(window=90).mean() # 輔助指標13
            return df
        return None
    except:
        return None

df = get_clean_data()

# 3. 核心 40 項紅綠燈邏輯運算
if df is not None and len(df) >= 4:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    open_p = df.iloc[0]['Open']
    day_high = df['High'].max()
    day_low = df['Low'].min()
    diff = day_high - day_low

    # --- [買進信號池 (🔴)] ---
    b_sigs = []
    # 開盤連續四根有連續三根紅K
    if all(df['Close'].iloc[1:4] > df['Open'].iloc[1:4]): b_sigs.append("B0:開盤三紅")
    # 1.回檔到高點0.382 | 2.跌破0.382再度往上
    if last['Close'] >= (day_low + diff * 0.382): b_sigs.append("B1/2:0.382支撐")
    # 3.靠近高點 0.618
    if abs(last['Close'] - (day_low + diff * 0.618)) < (diff * 0.05): b_sigs.append("B3:近0.618")
    # 4.突破前高量破前高 | 5.低低高高
    if last['Close'] > prev['High'] and last['Volume'] > prev['Volume']: b_sigs.append("B4/5:突破量增")
    # 6.長紅拉回未破底 | 9.帶量突破開盤價
    if last['Close'] > open_p and last['Volume'] > df['Volume'].mean(): b_sigs.append("B6/9:突破開盤")
    # 10.突破8:45-9:05高點 (簡化為前5根K)
    if last['Close'] > df['High'].iloc[:5].max(): b_sigs.append("B10:突破早盤方框")
    # 11.5MA之上 | 12.20MA之上
    if last['Close'] > last['5MA'] and last['Close'] > last['20MA']: b_sigs.append("B11/12:均線之上")
    # 13.20MA穿過90MA且上揚
    if last['20MA'] > last['90MA'] and last['20MA'] > prev['20MA']: b_sigs.append("B13:均線金叉")
    # 14.連三紅K | 15.三黑被三紅超越
    if all(df['Close'].tail(3) > df['Open'].tail(3)): b_sigs.append("B14/15:連三紅")
    # 18.突破早盤最大量K高點 | 20.量破5000站穩高點
    if last['Volume'] > 5000 and last['Close'] >= last['High']: b_sigs.append("B18/20:爆量突破")

    # --- [賣出信號池 (🟢)] ---
    s_sigs = []
    # 開盤連續四根有連續三根綠K
    if all(df['Close'].iloc[1:4] < df['Open'].iloc[1:4]): s_sigs.append("S0:開盤三綠")
    # 1.跌破0.618 | 2.反彈未過0.618
    if last['Close'] < (day_low + diff * 0.618): s_sigs.append("S1/2:破0.618")
    # 3.反彈未破0.382轉弱 | 4.高點越低
    if last['High'] < prev['High']: s_sigs.append("S3/4:高點降低")
    # 8.開盤價之下 | 9.跌破開盤往上未果
    if last['Close'] < open_p: s_sigs.append("S8/9:開盤價之下")
    # 10.跌破8:45-9:05低點
    if last['Close'] < df['Low'].iloc[:5].min(): s_sigs.append("S10:破早盤下緣")
    # 11.跌破5MA | 12.均線死叉
    if last['Close'] < last['5MA'] or last['10MA'] < last['20MA']: s_sigs.append("S11/12:均線轉弱")
    # 14.連三綠K | 15.三紅被三綠追平
    if all(df['Close'].tail(3) < df['Open'].tail(3)): s_sigs.append("S14/15:連三綠")
    # 17.跌破最大量K低點 | 19.量破5000且低於下緣
    if last['Volume'] > 5000 and last['Close'] <= last['Low']: s_sigs.append("S17/19:爆量跌破")

    # --- [燈號邏輯與互斥規則] ---
    # 每5個信號亮一燈
    r_raw = min(3, (1 if "B0:開盤三紅" in b_sigs else 0) + (len(b_sigs) // 5))
    g_raw = min(3, (1 if "S0:開盤三綠" in s_sigs else 0) + (len(s_sigs) // 5))
    
    # 互斥熄滅規則：紅綠燈相互抵銷
    f_red = max(0, r_raw - g_raw)
    f_green = max(0, g_raw - r_raw)

    # 4. 戰情視覺化 (適配 v1.19.0)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔴 買進戰情燈")
        st.write("🔴" * f_red + "⚪" * (3 - f_red))
        st.info(f"達成買入信號: {len(b_sigs)}")
        st.caption("細節: " + ", ".join(b_sigs))
        
    with c2:
        st.subheader("🟢 賣出戰情燈")
        st.write("🟢" * f_green + "⚪" * (3 - f_green))
        st.info(f"達成賣出信號: {len(s_sigs)}")
        st.caption("細節: " + ", ".join(s_sigs))

    st.markdown("---") # 替代 st.divider
    
    # 即時看板
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("即時點位", f"{last['Close']:,.0f}")
    m2.metric("5MA位階", f"{last['5MA']:,.1f}")
    m3.metric("今日振幅", f"{diff:,.0f}")
    m4.metric("最新成交量", f"{int(last['Volume'])}")

    # 強哥位階 (0.618 / 0.382)
    st.error(f"🚀 壓力區 (0.618)：**{day_low + diff * 0.618:,.2f}**")
    st.success(f"🛡️ 支撐區 (0.382)：**{day_low + diff * 0.382:,.2f}**")

else:
    st.error("❌ 數據同步中，請確保 GitHub 上的 requirements.txt 已更新並點擊 Reboot。")
