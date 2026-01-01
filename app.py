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

st.set_page_config(page_title="Procurement Analysis Dashboard", layout="wide")

# ==========================================================
# CSS Styling (unchanged except tighter top spacing)
# ==========================================================
st.markdown(f"""
<style>
body {{ font-family:Segoe UI;background:#FAFAFA;margin:10px; }}

.kpi-card {{
 background:white;
 border-radius:12px;
 padding:14px 16px;
 box-shadow:0 4px 10px rgba(0,0,0,0.12);
 border-left:6px solid {HEADER_BLUE};
}}

.kpi-title {{ font-size:13px;color:#546E7A;font-weight:600; }}
.kpi-value {{ font-size:22px;font-weight:700;color:{HEADER_BLUE}; }}

.stButton button {{
    background-color: {HEADER_BLUE};
    color:white;
}}

hr {{ margin:20px 0; }}
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
        ["Equipment name", "Service", "QTY Requested", "Unit Price RWF",
         "Has Contract?", "Delivery Status"]
    ].copy()

    df.columns = [
        "Equipment", "Service", "Quantity", "Unit_Price_RWF",
        "Has Contract?", "Delivery Status"
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
# LAST UPDATED
# ==========================================================
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
# TOP 10
# ==========================================================
def top10(df_in, metric):
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates(subset=["Equipment_wrapped"])
        return df_unique.groupby("Equipment_wrapped", as_index=False)[metric].max().sort_values(metric, ascending=False).head(10)
    return df_in.groupby("Equipment_wrapped", as_index=False)[metric].sum().sort_values(metric, ascending=False).head(10)

# ==========================================================
# BAR CHART (unchanged)
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
    fig.update_traces(textposition="outside")
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=650,
        margin=dict(t=140, b=200),
        xaxis_title="Equipment",
        yaxis_title=y_label
    )

    y0, y1 = 1.02, 1.12
    fig.add_shape(type="rect", xref="paper", yref="paper", x0=0, x1=1, y0=y0, y1=y1, fillcolor=HEADER_BLUE, line_width=0)
    fig.add_annotation(x=0.5, y=(y0+y1)/2, xref="paper", yref="paper",
                       text=f"<b>{title}</b>", showarrow=False,
                       font=dict(color="white", size=15))

    fig.update_xaxes(tickangle=-45)
    return fig

# ==========================================================
# PIE CHART (NEW)
# ==========================================================
def pie_chart(df_in, column, title):
    pie_df = df_in[column].fillna("Unknown").astype(str).value_counts().reset_index()
    pie_df.columns = [column, "Count"]

    fig = px.pie(
        pie_df,
        names=column,
        values="Count",
        hole=0.45,
        title=title
    )

    fig.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>"
    )

    fig.update_layout(height=420)
    return fig

# ==========================================================
# HEADER
# ==========================================================
st.markdown("<h1>Procurement Analysis Dashboard (USD)</h1>", unsafe_allow_html=True)

# ==========================================================
# KPIs
# ==========================================================
k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Budget</div><div class='kpi-value'>${int(df['Total_Price'].sum()):,}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Quantity</div><div class='kpi-value'>{int(df['Quantity'].sum()):,}</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Services</div><div class='kpi-value'>{df['Service'].nunique()}</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi-card'><div class='kpi-title'>Equipment Items</div><div class='kpi-value'>{df['Equipment'].nunique()}</div></div>", unsafe_allow_html=True)

# ==========================================================
# ✅ PIE CHARTS — DIRECTLY BELOW KPIs (AS REQUESTED)
# ==========================================================
st.markdown("### 📦 Procurement Status Overview")

p1, p2 = st.columns(2)
with p1:
    st.plotly_chart(pie_chart(df, "Has Contract?", "Contract Coverage"), use_container_width=True)
with p2:
    st.plotly_chart(pie_chart(df, "Delivery Status", "Delivery Status Distribution"), use_container_width=True)

st.markdown("---")

# ==========================================================
# DOWNLOAD
# ==========================================================
st.download_button(
    "⬇️ Download Full Data (CSV)",
    df.to_csv(index=False),
    file_name="procurement_data.csv",
    mime="text/csv"
)

# ==========================================================
# TABS (UNCHANGED)
# ==========================================================
service_list = sorted(df["Service"].unique())
tabs = st.tabs(["Overview"] + service_list)

with tabs[0]:
    st.plotly_chart(bar_chart(top10(df, "Unit_Price"), "Top 10 Equipment by Unit Price (USD)", "Unit_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Total_Price"), "Top 10 Equipment by Total Price (USD)", "Total_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Quantity"), "Top 10 Equipment by Quantity", "Quantity", "Quantity"), use_container_width=True)

for i, service in enumerate(service_list, start=1):
    with tabs[i]:
        d = df[df["Service"] == service]
        st.plotly_chart(bar_chart(top10(d, "Unit_Price"), f"Top 10 Unit Price – {service}", "Unit_Price", "USD", True), use_container_width=True)
        st.plotly_chart(bar_chart(top10(d, "Total_Price"), f"Top 10 Total Price – {service}", "Total_Price", "USD", True), use_container_width=True)
        st.plotly_chart(bar_chart(top10(d, "Quantity"), f"Top 10 Quantity – {service}", "Quantity", "Quantity"), use_container_width=True)
