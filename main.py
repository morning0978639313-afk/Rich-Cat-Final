import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pytz

# --- 1. 初始化與時區 ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=3000, key="tmf_stable_engine")
st.set_page_config(page_title="TMF 3分K 穩定監控", layout="wide")

# --- 2. 自動計算合約月份 (TMF + YYYYMM) ---
def get_current_tmf_id():
    now = datetime.now(tw_tz)
    # 簡單邏輯：抓當月。若過結算日則需更複雜，暫以當月為主
    return f"TMF{now.strftime('%Y%m')}"

# --- 3. 穩定版數據抓取函式 ---
@st.cache_data(ttl=10) # 10秒內不重複請求 API，保護 IP
def fetch_data_resilient(contract_id):
    api = DataLoader()
    now_tw = datetime.now(tw_tz)
    
    # 嘗試抓取今日 Ticks
    try:
        df = api.taiwan_futures_tick(futures_id=contract_id, date=now_tw.strftime('%Y-%m-%d'))
        
        # 若今日無資料 (例如早盤剛開)，嘗試抓取昨日
        if df is None or df.empty or 'price' not in df.columns:
            yesterday = (now_tw - timedelta(days=1)).strftime('%Y-%m-%d')
            df = api.taiwan_futures_tick(futures_id=contract_id, date=yesterday)
        
        return df
    except:
        return pd.DataFrame()

# --- 4. 畫面顯示 ---
st.title("TMF 3分K 交易監控系統")
st.write(f"⏰ **台灣時間**: {datetime.now(tw_tz).strftime('%H:%M:%S')} | **監控合約**: {get_current_tmf_id()}")

# 執行抓取
contract_id = get_current_tmf_id()
df_raw = fetch_data_resilient(contract_id)

if not df_raw.empty:
    # 3分K 轉換與 40 個指標運算 (縮略示範)
    df_raw['date'] = pd.to_datetime(df_raw['date'] + ' ' + df_raw['time'])
    df_raw = df_raw.set_index('date')
    df_3m = df_raw['price'].resample('3min').ohlc()
    df_3m['volume'] = df_raw['qty'].resample('3min').sum()
    df = df_3m.dropna().reset_index()

    # 指標邏輯 (Rich 修正版：多空並存)
    # 假設計算出 1 紅 2 綠
    r_cnt, g_cnt = 1, 1 # 這裡會接你的 40 個指標計算結果
    
    # --- UI 燈號 (保持發光感) ---
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🔴 買進紅燈")
        st.markdown("".join([f'<div style="width:70px;height:70px;background:{"#FF0000" if i<r_cnt else "#220000"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow: {"0 0 20px #FF0000" if i<r_cnt else "none"};"></div>' for i in range(3)]), unsafe_allow_html=True)
    with c2:
        st.markdown("### 🟢 賣出綠燈")
        st.markdown("".join([f'<div style="width:70px;height:70px;background:{"#00FF00" if i<g_cnt else "#002200"};border-radius:50%;display:inline-block;margin:10px;border:3px solid white;box-shadow: {"0 0 20px #00FF00" if i<g_cnt else "none"};"></div>' for i in range(3)]), unsafe_allow_html=True)

    st.markdown("---")
    st.dataframe(df.tail(5))
else:
    st.error("⚠️ 暫時無法獲取即時數據。請確認：")
    st.write("1. 目前是否為 TMF 交易時段？")
    st.write(f"2. FinMind 是否支援合約 {contract_id}？")
    st.info("💡 建議：若一直無法抓取，建議註冊 Fugle (富果) API，穩定性會提升 10 倍。")
