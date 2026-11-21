import streamlit as st
import pandas as pd
from sqlalchemy import text
from engine import engine, DB_BACKEND, NORMALS, to_scale, init_database, predict_and_cache_year

st.set_page_config(page_title="Monsoon prediction For Kerala :- Astro-Meteorological Forecasting System", layout="wide")
init_database()

st.title("🌧️ Monsoon prediction For Kerala :- Astro-Meteorological Forecasting System")
st.caption("V4 Refined Sidereal Engine | PostgreSQL Cached | 50-Year IMD Master History (1975–2026) | Units: 1–10 Scale, mm & Liters/m² (1 mm = 1 L/m²)")

with st.sidebar:
    st.header("Forecast Controls")
    sel_year = st.number_input("Select Target Year (1901–2100)", min_value=1901, max_value=2100, value=2027, step=1)
    if st.button("Compute & Cache Selected Year"):
        with st.spinner(f"Running V4 Ephemeris Engine for {sel_year}..."):
            predict_and_cache_year(int(sel_year))
        st.success(f"Year {sel_year} computed and stored in PostgreSQL!")

    st.divider()
    db_label = "PostgreSQL Server (Connected)" if DB_BACKEND == "postgresql" else "Standalone Local DB (Zero-Config)"
    st.info(f"**Database Engine:** {db_label}")
    st.markdown("**Pre-Cached Years in DB:** 2026–2030 + 1975–2026 IMD Actuals")

predict_and_cache_year(int(sel_year))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. General Kerala Annual",
    "2. 12-Month Kerala Forecast",
    "3. 9-Grid Kurma × 12 Months",
    "4. Dam Catchment Areas",
    "5. 50-Yr IMD Master DB"
])

with tab1:
    st.subheader(f"General Kerala Annual Outlook — {sel_year}")
    df_ann = pd.read_sql(text("""
        SELECT year, ROUND(AVG(score_1_to_10), 2) AS avg_score_1_10,
               SUM(predicted_mm) AS annual_mm, SUM(predicted_l_per_m2) AS annual_l_m2,
               ROUND(AVG(departure_pct), 1) AS avg_departure_pct
        FROM rainfall_predictions WHERE sector_id = 0 AND year BETWEEN 2026 AND 2030
        GROUP BY year ORDER BY year
    """), engine)
    st.markdown("#### Pre-Cached 5-Year Annual Outlook (2026–2030)")
    st.dataframe(df_ann, use_container_width=True)
    st.markdown("##### 5-Year Annual Rainfall Trend (mm / L per m²)")
    st.bar_chart(df_ann.set_index("year")["annual_mm"], use_container_width=True)

    sel_ann = pd.read_sql(text("""
        SELECT ROUND(AVG(score_1_to_10), 2) AS score, SUM(predicted_mm) AS mm, SUM(predicted_l_per_m2) AS lm2
        FROM rainfall_predictions WHERE sector_id = 0 AND year = :y
    """), engine, params={"y": int(sel_year)}).iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{sel_year} Avg Intensity (1–10)", f"{sel_ann['score']} / 10")
    c2.metric(f"{sel_year} Predicted Depth", f"{sel_ann['mm']:,.1f} mm")
    c3.metric(f"{sel_year} Water Volume / Area", f"{sel_ann['lm2']:,.1f} L/m²")

with tab2:
    st.subheader(f"12-Month Statewide Kerala Forecast — {sel_year}")
    df_m = pd.read_sql(text("""
        SELECT month, score_1_to_10, predicted_mm, predicted_l_per_m2, departure_pct, astro_notes
        FROM rainfall_predictions WHERE sector_id = 0 AND year = :y ORDER BY month
    """), engine, params={"y": int(sel_year)})
    st.dataframe(df_m, use_container_width=True)
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown("##### Monthly Predicted Rainfall (mm / L per m²)")
        st.bar_chart(df_m.set_index("month")["predicted_mm"], use_container_width=True)
    with c_right:
        st.markdown("##### Monthly Astro-Intensity Curve (1–10 Scale)")
        st.line_chart(df_m.set_index("month")["score_1_to_10"], use_container_width=True)
    st.download_button(f"Download {sel_year} 12-Month CSV", df_m.to_csv(index=False), f"kerala_12m_{sel_year}.csv")

with tab3:
    st.subheader(f"9-Grid Kurma Chakra × 12 Months — {sel_year}")
    unit_choice = st.radio("Display Metric:", ["1–10 Intensity Scale", "Millimeters (mm)", "Liters per m² (L/m²)"], horizontal=True)
    col_map = {"1–10 Intensity Scale": "score_1_to_10", "Millimeters (mm)": "predicted_mm", "Liters per m² (L/m²)": "predicted_l_per_m2"}
    df_9 = pd.read_sql(text("""
        SELECT k.sector_name, p.month, p.score_1_to_10, p.predicted_mm, p.predicted_l_per_m2
        FROM rainfall_predictions p JOIN kurma_sectors_dams k ON p.sector_id = k.sector_id
        WHERE p.year = :y ORDER BY k.sector_id, p.month
    """), engine, params={"y": int(sel_year)})
    piv = df_9.pivot(index="sector_name", columns="month", values=col_map[unit_choice])
    st.dataframe(piv, use_container_width=True)

with tab4:
    st.subheader(f"Kerala Dam Catchments & River Basins — {sel_year}")
    df_dams = pd.read_sql(text("""
        SELECT k.sector_name, k.nakshatras, k.river_basins, k.major_dams,
               ROUND(AVG(p.score_1_to_10), 2) AS annual_score,
               SUM(p.predicted_mm) AS annual_catchment_mm,
               SUM(p.predicted_l_per_m2) AS annual_l_per_m2
        FROM kurma_sectors_dams k JOIN rainfall_predictions p ON k.sector_id = p.sector_id
        WHERE p.year = :y GROUP BY k.sector_id, k.sector_name, k.nakshatras, k.river_basins, k.major_dams
        ORDER BY k.sector_id
    """), engine, params={"y": int(sel_year)})
    st.dataframe(df_dams, use_container_width=True)
    st.markdown("##### Annual Catchment Volume by Sector (mm / L per m²)")
    st.bar_chart(df_dams.set_index("sector_name")["annual_catchment_mm"], use_container_width=True)

with tab5:
    st.subheader("Stored 50-Year IMD Master History (1975–2026) — Zero Re-Download Needed")
    yr_filter = st.slider("Filter Historical Years", 1975, 2026, (2018, 2026))
    df_hist = pd.read_sql(text("""
        SELECT * FROM imd_master_history WHERE year BETWEEN :y1 AND :y2 ORDER BY year DESC, month ASC
    """), engine, params={"y1": yr_filter[0], "y2": yr_filter[1]})
    st.dataframe(df_hist, use_container_width=True)

import io
with st.sidebar:
    st.divider()
    st.subheader("Export Full Report")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_ann.to_excel(writer, sheet_name="5Yr_Annual_Outlook", index=False)
        df_m.to_excel(writer, sheet_name=f"{sel_year}_12M_Statewide", index=False)
        piv.to_excel(writer, sheet_name=f"{sel_year}_9Sector_Grid")
        df_dams.to_excel(writer, sheet_name=f"{sel_year}_Dam_Catchments", index=False)
    st.download_button(
        label=f"📊 Download {sel_year} Full Excel (.xlsx)",
        data=buf.getvalue(),
        file_name=f"Kerala_Monsoon_Forecast_{sel_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
