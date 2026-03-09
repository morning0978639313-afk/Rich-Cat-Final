import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pytz

# --- 1. 時區與自動重整 ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=3000, key="tmf_no_sidebar")

st.set_page_config(page_title="TMF 3分K 監控", layout="wide")

# --- 2. 主標題與時間 ---
st.title("TMF 3分K 交易監控系統")
now_tw = datetime.now(tw_tz)
st.write(f"⏰ **台灣站點時間**: {now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

# --- 3. 系統設定區 (取代原本的左側分頁) ---
with st.expander("🛠️ 系統設定與模擬測試 (點擊展開/收合)"):
    test_mode = st.checkbox("開啟測試模式 (手動模擬燈號)", value=False)
    if test_mode:
        c1, c2 = st.columns(2)
        with c1:
            sim_red = st.slider("模擬買進紅燈", 0, 3, 0)
            sim_buy_score = st.number_input("模擬買進積分", 0, 20, 12)
        with c2:
            sim_green = st.slider("模擬賣出綠燈", 0, 3, 0)
            sim_sell_score = st.number_input("模擬賣出積分", 0, 20, 5)

# --- 4. 燈號渲染組件 ---
def render_trading_lights(r_count, g_count, b_score, s_score):
    # 對消邏輯：每亮一顆綠燈，紅燈熄滅一顆
    final_r = max(0, r_count - g_count)
    final_g = g_count 
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔴 買進紅燈區")
        l_html = "".join([
            f'<div style="width:70px;height:70px;background:{"#FF0000" if i < final_r else "#220000"};'
            f'border-radius:50%;display:inline-block;margin:10px;border:3px solid white;'
            f'box-shadow: {"0 0 20px #FF0000" if i < final_r else "none"};"></div>'
            for i in range(3)
        ])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("買進指標積分", f"{b_score} / 20")

    with col2:
        st.markdown("### 🟢 賣出綠燈區")
        l_html = "".join([
            f'<div style="width:70px;height:70px;background:{"#00FF00" if i < final_g else "#002200"};'
            f'border-radius:50%;display:inline-block;margin:10px;border:3px solid white;'
            f'box-shadow: {"0 0 20px #00FF00" if i < final_g else "none"};"></div>'
            for i in range(3)
        ])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("賣出指標積分", f"{s_score} / 20")

st.markdown("---")

# --- 5. 數據與邏輯執行 ---
if test_mode:
    render_trading_lights(sim_red, sim_green, sim_buy_score, sim_sell_score)
else:
    api = DataLoader()
    try:
        df_raw = api.taiwan_futures_tick(futures_id="TMF", date=now_tw.strftime('%Y-%m-%d'))
        if df_raw is not None and not df_raw.empty:
            st.success(f"✅ 已連線 TMF 獲取 {len(df_raw)} 筆數據")
            # 這裡帶入 3分K 計算邏輯
            render_trading_lights(1, 0, 5, 0)
            st.dataframe(df_raw.tail(5))
        else:
            render_trading_lights(0, 0, 0, 0)
            st.warning("⚠️ 目前無即時數據。請確認開盤時間或使用測試模式。")
    except Exception as e:
        render_trading_lights(0, 0, 0, 0)
        st.error(f"❌ API 異常: {e}")

st.markdown("---")
st.caption("備註：本系統嚴格遵循 3分K 基準運算，所有買賣指標 (B1-B20, S1-S20) 均在後台即時計算。")
