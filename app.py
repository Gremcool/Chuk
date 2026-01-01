import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import StringIO
import re

# ==========================================================
# CONFIG
# ==========================================================
GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSf8Mw53Loetlm4LAdRkMFhvr7JQrlTwIxa_KbYENc-nZa3AYSO4nk9DSevduzQ3DCvhhLH9xryBwfu/pub?gid=13772104&single=true&output=csv"
USD_RATE = 1454
HEADER_BLUE = "#0D47A1"
LIGHT_BLUE = "#E8F1FF"

st.set_page_config(page_title="Procurement Analysis Dashboard", layout="wide")

# ==========================================================
# CSS Styling (TAB FIX IS HERE)
# ==========================================================
st.markdown(f"""
<style>
body {{ font-family:Segoe UI;background:#FAFAFA;margin:10px; }}

.kpi-card {{
 background:{LIGHT_BLUE};
 border-radius:12px;
 padding:14px 16px;
 box-shadow:0 4px 10px rgba(0,0,0,0.10);
 border-left:6px solid {HEADER_BLUE};
}}

.kpi-title {{ font-size:13px;color:#37474F;font-weight:600; }}
.kpi-value {{ font-size:22px;font-weight:700;color:{HEADER_BLUE}; }}

/* ===== TRUE FIREFOX-STYLE TABS ===== */
.stTabs [data-baseweb="tab-list"] {{
 gap: 0px !important;          /* <<< removes invisible spacing */
}}

.stTabs [data-baseweb="tab"] {{
 background:{LIGHT_BLUE};
 padding:8px 14px;
 margin:0 !important;          /* <<< no spacing */
 border-radius:6px 6px 0 0;
 border:1px solid rgba(0,0,0,0.25);
 font-weight:600;
}}

.stTabs [data-baseweb="tab"]:not(:first-child) {{
 margin-left:-1px !important;  /* <<< overlap borders like Firefox */
}}

.stTabs [aria-selected="true"] {{
 background:{HEADER_BLUE};
 color:white;
 border:1px solid {HEADER_BLUE};
 z-index:2;
}}

.stButton button {{
 background-color:{HEADER_BLUE};
 color:white;
}}

hr {{ margin:12px 0; }}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# LOAD DATA
# ==========================================================
@st.cache_data(ttl=30)
def load_data():
    r = requests.get(GOOGLE_SHEET_CSV)
    r.raise_for_status()
    df_raw = pd.read_csv(StringIO(r.text))

    df = df_raw[
        ["Equipment name", "Service", "QTY Requested",
         "Unit Price RWF", "Has Contract?", "Delivery Status"]
    ].copy()

    df.columns = [
        "Equipment", "Service", "Quantity",
        "Unit_Price_RWF", "Has Contract?", "Delivery Status"
    ]

    df["Equipment"] = df["Equipment"].astype(str).str.strip()
    df["Service"] = df["Service"].astype(str).str.strip()
    df.loc[df["Service"].isin(["", "nan", "None"]), "Service"] = "Unknown"

    def clean_numeric(col):
        col = col.astype(str).str.replace(",", "").str.replace(" ", "")
        col = col.replace({"NA": "0", "-": "0", "": "0", "nan": "0", "None": "0"})
        col = col.apply(lambda x: re.sub(r"[^\d.]", "", x) if pd.notnull(x) else "0")
        return pd.to_numeric(col, errors="coerce").fillna(0)

    df["Quantity"] = clean_numeric(df["Quantity"])
    df["Unit_Price_RWF"] = clean_numeric(df["Unit_Price_RWF"])

    df["Unit_Price"] = df["Unit_Price_RWF"] / USD_RATE
    df["Total_Price"] = df["Unit_Price"] * df["Quantity"]

    return df

df = load_data()

# ==========================================================
# HEADER
# ==========================================================
st.markdown(
    f"<h1 style='color:{HEADER_BLUE};margin-bottom:5px;'>Procurement Analysis Dashboard (USD)</h1>",
    unsafe_allow_html=True
)
st.caption(
    f"📊 **Data source:** Google Sheet  |  "
    f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

# ==========================================================
# WRAP LABEL
# ==========================================================
def wrap_text(text, width=30):
    if not isinstance(text, str):
        return ""
    words, lines, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) <= width:
            line += (" " if line else "") + w
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return "<br>".join(lines[:2])

df["Equipment_wrapped"] = df["Equipment"].apply(wrap_text)

# ==========================================================
# KPI CARDS
# ==========================================================
k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Budget</div><div class='kpi-value'>${int(df['Total_Price'].sum()):,}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Quantity</div><div class='kpi-value'>{int(df['Quantity'].sum()):,}</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Services</div><div class='kpi-value'>{df['Service'].nunique()}</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi-card'><div class='kpi-title'>Equipment Items</div><div class='kpi-value'>{df['Equipment'].nunique()}</div></div>", unsafe_allow_html=True)

# ==========================================================
# PIE CHART
# ==========================================================
def pie_chart(df_in, column, title):
    pie_df = df_in[column].fillna("Unknown").astype(str).value_counts().reset_index()
    pie_df.columns = [column, "Count"]

    fig = px.pie(
        pie_df,
        names=column,
        values="Count",
        hole=0.45,
        title=f"<b style='color:{HEADER_BLUE}'>{title}</b>"
    )

    fig.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{{label}}</b><br>Count: %{{value}}<br>Share: %{{percent}}<extra></extra>"
    )

    fig.update_layout(height=360, margin=dict(t=60, b=30))
    return fig

# ==========================================================
# TOP 10
# ==========================================================
def top10(df_in, metric):
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates(subset=["Equipment_wrapped"])
        return df_unique.groupby("Equipment_wrapped", as_index=False)[metric].max().sort_values(metric, ascending=False).head(10)
    return df_in.groupby("Equipment_wrapped", as_index=False)[metric].sum().sort_values(metric, ascending=False).head(10)

# ==========================================================
# BAR CHART
# ==========================================================
def bar_chart(df_in, title, y_col, y_label, is_currency=False):
    fig = px.bar(
        df_in,
        x="Equipment_wrapped",
        y=y_col,
        color="Equipment_wrapped",
        color_discrete_sequence=px.colors.qualitative.Set3,
        text=df_in[y_col].apply(lambda x: f"${int(x):,}" if is_currency else f"{int(x):,}")
    )

    fig.update_traces(
        textposition="outside",
        textfont=dict(color="black"),
        marker_line_width=1.8,
        marker_line_color="black"
    )

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=650,
        margin=dict(t=140, b=200),
        xaxis_title="Equipment",
        yaxis_title=y_label
    )

    fig.update_xaxes(showline=True, linewidth=2, linecolor="black", tickfont=dict(color="black"), tickangle=-45)
    fig.update_yaxes(showline=True, linewidth=2, linecolor="black", tickfont=dict(color="black"))

    y0, y1 = 1.02, 1.12
    fig.add_shape(type="rect", xref="paper", yref="paper",
                  x0=0, x1=1, y0=y0, y1=y1,
                  fillcolor=HEADER_BLUE, line_width=0)

    fig.add_annotation(
        x=0.5, y=(y0 + y1) / 2,
        xref="paper", yref="paper",
        text=f"<b>{title}</b>",
        showarrow=False,
        font=dict(color="white", size=15),
        yanchor="middle"
    )

    return fig

# ==========================================================
# DOWNLOAD
# ==========================================================
st.download_button("⬇️ Download Full Data (CSV)", df.to_csv(index=False), "procurement_data.csv")

# ==========================================================
# TABS
# ==========================================================
service_list = sorted(df["Service"].unique())
tabs = st.tabs(["Overview"] + service_list)

with tabs[0]:
    st.markdown(f"<h3 style='color:{HEADER_BLUE};'>Procurement Status Overview</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.plotly_chart(pie_chart(df, "Has Contract?", "Contract Coverage"), use_container_width=True)
    c2.plotly_chart(pie_chart(df, "Delivery Status", "Delivery Status Distribution"), use_container_width=True)

    st.plotly_chart(bar_chart(top10(df, "Unit_Price"), "Top 10 Equipment by Unit Price (USD)", "Unit_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Total_Price"), "Top 10 Equipment by Total Price (USD)", "Total_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Quantity"), "Top 10 Equipment by Quantity", "Quantity", "Quantity"), use_container_width=True)

for i, service in enumerate(service_list, start=1):
    with tabs[i]:
        d = df[df["Service"] == service]

        c1, c2 = st.columns(2)
        c1.plotly_chart(pie_chart(d, "Has Contract?", f"Contract Coverage – {service}"), use_container_width=True)
        c2.plotly_chart(pie_chart(d, "Delivery Status", f"Delivery Status – {service}"), use_container_width=True)

        st.plotly_chart(bar_chart(top10(d, "Unit_Price"), f"Top 10 Unit Price – {service}", "Unit_Price", "USD", True), use_container_width=True)
        st.plotly_chart(bar_chart(top10(d, "Total_Price"), f"Top 10 Total Price – {service}", "Total_Price", "USD", True), use_container_width=True)
        st.plotly_chart(bar_chart(top10(d, "Quantity"), f"Top 10 Quantity – {service}", "Quantity", "Quantity"), use_container_width=True)
