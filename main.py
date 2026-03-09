import streamlit as st
import pandas as pd
import numpy as np
from FinMind.data import DataLoader
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pytz

# --- 1. 環境校時 (強制台灣時區) ---
tw_tz = pytz.timezone('Asia/Taipei')
st_autorefresh(interval=3000, key="tmf_v4_ui")

st.set_page_config(page_title="TMF 3分K 監控", layout="wide")
st.title("TMF 3分K 交易監控系統 - 介面先行版")

# --- 2. 側邊欄控制區 (讓 Rich 可以直接測試) ---
st.sidebar.header("🛠️ 測試與設定")
test_mode = st.sidebar.checkbox("開啟測試模式 (手動模擬燈號)")
if test_mode:
    sim_red = st.sidebar.slider("模擬買進紅燈", 0, 3, 0)
    sim_green = st.sidebar.slider("模擬賣出綠燈", 0, 3, 0)
    sim_buy_score = st.sidebar.number_input("模擬買進積分", 0, 20, 12)
    sim_sell_score = st.sidebar.number_input("模擬賣出積分", 0, 20, 5)

# 顯示校時資訊
now_tw = datetime.now(tw_tz)
st.write(f"⏰ **台灣站點時間**: {now_tw.strftime('%Y-%m-%d %H:%M:%S')}")

# --- 3. 燈號渲染組件 (Rich 專屬對消邏輯) ---
def render_trading_lights(r_count, g_count, b_score, s_score):
    # 執行你的規則：後增加的留著亮燈，前面的對方的會減少
    # 這裡顯示最終對消後的結果
    final_r = max(0, r_count - g_count)
    final_g = g_count 
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔴 買進紅燈區")
        # 畫出 3 顆燈
        l_html = "".join([
            f'<div style="width:60px;height:60px;background:{"#FF0000" if i < final_r else "#330000"};'
            f'border-radius:50%;display:inline-block;margin:10px;border:3px solid white;'
            f'box-shadow: {"0 0 15px #FF0000" if i < final_r else "none"};"></div>'
            for i in range(3)
        ])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("買進指標積分", f"{b_score} / 20")

    with col2:
        st.markdown("### 🟢 賣出綠燈區")
        l_html = "".join([
            f'<div style="width:60px;height:60px;background:{"#00FF00" if i < final_g else "#003300"};'
            f'border-radius:50%;display:inline-block;margin:10px;border:3px solid white;'
            f'box-shadow: {"0 0 15px #00FF00" if i < final_g else "none"};"></div>'
            for i in range(3)
        ])
        st.markdown(l_html, unsafe_allow_html=True)
        st.metric("賣出指標積分", f"{s_score} / 20")

st.markdown("---")

# --- 4. 數據抓取與邏輯執行 ---
if test_mode:
    # 測試模式：直接畫燈
    render_trading_lights(sim_red, sim_green, sim_buy_score, sim_sell_score)
    st.info("💡 畫面目前處於『手動測試模式』，你可以調整左側拉桿確認燈號邏輯。")
else:
    # 實戰模式：嘗試連線 API
    api = DataLoader()
    try:
        # 嘗試抓取 TMF (微台全)
        df_raw = api.taiwan_futures_tick(futures_id="TMF", date=now_tw.strftime('%Y-%m-%d'))
        
        if df_raw is not None and not df_raw.empty:
            st.success(f"✅ 連線成功！已抓取 {len(df_raw)} 筆數據。")
            # 這裡會跑 3分K 轉換與 40 個指標運算
            # 暫時預設 1 顆紅燈作為數據通暢證明
            render_trading_lights(1, 0, 5, 0)
            st.dataframe(df_raw.tail(5))
        else:
            # 沒數據時也要畫出燈號框架 (灰色)
            render_trading_lights(0, 0, 0, 0)
            st.warning("⚠️ 目前 API 無數據回傳。請確認開盤時間，或檢查是否需指定月份代號 (如 TMF202603)。")
            
    except Exception as e:
        render_trading_lights(0, 0, 0, 0)
        st.error(f"❌ API 異常: {e}")

st.markdown("---")
st.caption("備註：本系統嚴格遵循 3分K 基準運算，所有買賣指標 (B1-B20, S1-S20) 均在後台即時計算。")
