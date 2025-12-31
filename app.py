import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import StringIO

# ==========================================================
# CONFIG
# ==========================================================
GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTzHV5uRT-b-3-0uBub083j6tOTdPU7NFK_ESyMKuT0pYNwMaWHFNy9uU1u8miMOQ/pub?gid=1002181482&single=true&output=csv"
USD_RATE = 1454
HEADER_BLUE = "#0D47A1"

st.set_page_config(page_title="Procurement Analysis Dashboard", layout="wide")

# ==========================================================
# STYLING
# ==========================================================
st.markdown(f"""
<style>
body {{ font-family:Segoe UI;background:#FAFAFA; }}

.kpi-grid {{
 display:grid;
 grid-template-columns:repeat(4,1fr);
 gap:14px;
 margin-bottom:25px;
}}

.kpi-card {{
 background:white;
 border-radius:12px;
 padding:14px 16px;
 box-shadow:0 4px 10px rgba(0,0,0,0.12);
 border-left:6px solid {HEADER_BLUE};
}}

.kpi-title {{ font-size:13px;color:#546E7A;font-weight:600; }}
.kpi-value {{ font-size:22px;font-weight:700;color:{HEADER_BLUE}; }}

</style>
""", unsafe_allow_html=True)

# ==========================================================
# LOAD DATA (FIXED GOOGLE SHEETS FETCH)
# ==========================================================
@st.cache_data(ttl=30)
def load_data():
    r = requests.get(GOOGLE_SHEET_CSV)
    r.raise_for_status()
    df_raw = pd.read_csv(StringIO(r.text))

    df = df_raw[["Equipment name", "Service", "QTY Requested", "Unit Price RWF"]].copy()
    df.columns = ["Equipment", "Service", "Quantity", "Unit_Price_RWF"]

    df["Equipment"] = df["Equipment"].astype(str).str.strip()
    df["Service"] = df["Service"].astype(str).str.strip()
    df.loc[df["Service"].isin(["", "nan", "None"]), "Service"] = "Unknown"

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    df["Unit_Price_RWF"] = pd.to_numeric(df["Unit_Price_RWF"], errors="coerce").fillna(0)

    df["Unit_Price"] = df["Unit_Price_RWF"] / USD_RATE
    df["Total_Price"] = df["Unit_Price"] * df["Quantity"]

    return df

df = load_data()

# ==========================================================
# HEADER
# ==========================================================
st.markdown("<h1>Procurement Analysis Dashboard (USD)</h1>", unsafe_allow_html=True)
st.caption(f"📊 Data source: Google Sheet | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ==========================================================
# SEARCH (SERVICE FILTER REMOVED)
# ==========================================================
search_equipment = st.text_input("🔍 Search Equipment", placeholder="Type part of equipment name…")

df_f = df.copy()
if search_equipment:
    df_f = df_f[df_f["Equipment"].str.contains(search_equipment, case=False)]

# ==========================================================
# WRAP LABEL
# ==========================================================
def wrap_text(text, width=30):
    words, lines, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) <= width:
            line += (" " if line else "") + w
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return "<br>".join(lines[:2])

df_f["Equipment_wrapped"] = df_f["Equipment"].apply(wrap_text)

# ==========================================================
# TOP 10 LOGIC (UNCHANGED)
# ==========================================================
def top10(df_in, metric):
    if df_in.empty:
        return df_in
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates(subset=["Equipment_wrapped"])
        grouped = df_unique.groupby("Equipment_wrapped", as_index=False)[metric].max()
    else:
        grouped = df_in.groupby("Equipment_wrapped", as_index=False)[metric].sum()
    return grouped.sort_values(metric, ascending=False).head(10)

# ==========================================================
# BAR CHART (FIXED HEADER CENTER + BAR VISIBILITY)
# ==========================================================
def bar_chart(df_in, title, y_col, y_label, is_currency=False):
    if df_in.empty:
        st.info("No data available for this selection.")
        return None

    ymax = df_in[y_col].max() * 1.15 if df_in[y_col].max() > 0 else 1

    fig = px.bar(
        df_in,
        x="Equipment_wrapped",
        y=y_col,
        color="Equipment_wrapped",
        color_discrete_sequence=px.colors.qualitative.Set3,
        text=df_in[y_col].apply(lambda x: f"${int(x):,}" if is_currency else f"{int(x):,}")
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=650,
        margin=dict(t=90, b=200),
        xaxis_title="Equipment",
        yaxis_title=y_label,
        yaxis=dict(range=[0, ymax])
    )

    # HEADER BANNER (VERTICALLY CENTERED)
    fig.add_shape(
        type="rect",
        xref="paper", yref="paper",
        x0=0, x1=1,
        y0=1.04, y1=1.14,
        fillcolor=HEADER_BLUE,
        line_width=0
    )

    fig.add_annotation(
        x=0.5, y=1.09,
        xref="paper", yref="paper",
        text=f"<b>{title}</b>",
        showarrow=False,
        font=dict(color="white", size=15),
        xanchor="center",
        yanchor="middle"
    )

    fig.update_xaxes(tickangle=-45)
    return fig

# ==========================================================
# KPIs
# ==========================================================
k1,k2,k3,k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Budget</div><div class='kpi-value'>${int(df_f['Total_Price'].sum()):,}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Quantity</div><div class='kpi-value'>{int(df_f['Quantity'].sum()):,}</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Services</div><div class='kpi-value'>{df_f['Service'].nunique()}</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi-card'><div class='kpi-title'>Equipment Items</div><div class='kpi-value'>{df_f['Equipment'].nunique()}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================================
# SERVICE BUDGET TABLE (RESTORED)
# ==========================================================
st.subheader("Service Budget Summary")

service_budget = (
    df_f.groupby("Service", as_index=False)["Total_Price"]
    .sum()
    .sort_values("Total_Price", ascending=False)
)

service_budget.loc[len(service_budget)] = ["TOTAL", service_budget["Total_Price"].sum()]
service_budget["Total_Price"] = service_budget["Total_Price"].apply(lambda x: f"${int(x):,}")

st.dataframe(service_budget, use_container_width=True)

# ==========================================================
# TABS (ALL SERVICES CLICKABLE)
# ==========================================================
services = sorted(df_f["Service"].unique())
tabs = st.tabs(["Overview"] + services)

with tabs[0]:
    for metric, title, label, cur in [
        ("Unit_Price","Top 10 Equipment by Unit Price (USD)","USD",True),
        ("Total_Price","Top 10 Equipment by Total Price (USD)","USD",True),
        ("Quantity","Top 10 Equipment by Quantity","Quantity",False)
    ]:
        fig = bar_chart(top10(df_f,metric), title, metric, label, cur)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

for i, service in enumerate(services, start=1):
    with tabs[i]:
        d = df_f[df_f["Service"] == service]
        for metric, label, cur in [
            ("Unit_Price","USD",True),
            ("Total_Price","USD",True),
            ("Quantity","Quantity",False)
        ]:
            fig = bar_chart(top10(d,metric), f"Top 10 {metric.replace('_',' ')} – {service}", metric, label, cur)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
