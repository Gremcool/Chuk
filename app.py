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
# CSS (UNCHANGED)
# ==========================================================
st.markdown(f"""
<style>
.block-container {{ padding-top: 1.5rem !important; }}

.stTabs {{
    position: sticky;
    top: 0;
    background: #FAFAFA;
    z-index: 100;
    padding-top: 6px;
}}

.kpi-card {{
 background:{LIGHT_BLUE};
 border-radius:12px;
 padding:14px 16px;
 box-shadow:0 4px 10px rgba(0,0,0,0.10);
 border-left:6px solid {HEADER_BLUE};
}}

.kpi-title {{ font-size:13px;color:#37474F;font-weight:600; }}
.kpi-value {{ font-size:22px;font-weight:700;color:{HEADER_BLUE}; }}

.stTabs [data-baseweb="tab-list"] {{ gap:0px !important; }}

.stTabs [data-baseweb="tab"] {{
 background:{LIGHT_BLUE};
 padding:8px 14px;
 margin:0 !important;
 border-radius:6px 6px 0 0;
 border:1px solid rgba(0,0,0,0.25);
 font-weight:600;
}}

.stTabs [data-baseweb="tab"]:not(:first-child) {{
 margin-left:-1px !important;
}}

.stTabs [aria-selected="true"] {{
 background:{HEADER_BLUE};
 color:white;
 border:1px solid {HEADER_BLUE};
 z-index:2;
}}
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
        ["Equipment name", "Department", "Service", "QTY Requested",
         "Unit Price RWF", "Has Contract?", "Delivery Status"]
    ].copy()

    df.columns = [
        "Equipment", "Department", "Service", "Quantity",
        "Unit_Price_RWF", "Has Contract?", "Delivery Status"
    ]

    for col in ["Equipment", "Department", "Service"]:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["", "nan", "None"]), col] = "Unknown"

    def clean_numeric(col):
        col = col.astype(str).str.replace(",", "").str.replace(" ", "")
        col = col.replace({"NA": "0", "-": "0", "": "0", "nan": "0", "None": "0"})
        col = col.apply(lambda x: re.sub(r"[^\d.]", "", x))
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
    f"<h1 style='color:{HEADER_BLUE}; margin-top:-10px;'>Procurement Analysis Dashboard (USD)</h1>",
    unsafe_allow_html=True
)
st.caption(
    f"📊 **Data source:** Google Sheet  |  "
    f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

# ==========================================================
# WRAP TEXT
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

df["Equipment_wrapped"] = df["Equipment"].apply(wrap_text)

# ==========================================================
# KPI CARDS
# ==========================================================
k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Budget</div><div class='kpi-value'>${int(df['Total_Price'].sum()):,}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Quantity</div><div class='kpi-value'>{int(df['Quantity'].sum()):,}</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Departments</div><div class='kpi-value'>{df['Department'].nunique()}</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi-card'><div class='kpi-title'>Services</div><div class='kpi-value'>{df['Service'].nunique()}</div></div>", unsafe_allow_html=True)
k5.markdown(f"<div class='kpi-card'><div class='kpi-title'>Equipment Items</div><div class='kpi-value'>{df['Equipment'].nunique()}</div></div>", unsafe_allow_html=True)

# ==========================================================
# CHART HELPERS (UNCHANGED)
# ==========================================================
def pie_chart(df_in, column, title):
    pie_df = df_in[column].fillna("Unknown").value_counts().reset_index()
    pie_df.columns = [column, "Count"]

    fig = px.pie(
        pie_df,
        names=column,
        values="Count",
        hole=0.45,
        title=f"<b style='color:{HEADER_BLUE}'>{title}</b>"
    )

    fig.update_traces(textinfo="percent+label", textfont=dict(size=14, color="black"))
    fig.update_layout(height=320, margin=dict(t=55, b=20),
                      legend=dict(font=dict(size=14)))
    return fig

def top10(df_in, metric):
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates("Equipment_wrapped")
        return df_unique.groupby("Equipment_wrapped", as_index=False)[metric].max() \
                        .sort_values(metric, ascending=False).head(10)
    return df_in.groupby("Equipment_wrapped", as_index=False)[metric].sum() \
                .sort_values(metric, ascending=False).head(10)

def bar_chart(df_in, title, y_col, y_label, is_currency=False):
    fig = px.bar(
        df_in,
        x="Equipment_wrapped",
        y=y_col,
        color="Equipment_wrapped",
        color_discrete_sequence=px.colors.qualitative.Set3,
        text=df_in[y_col].apply(lambda x: f"${int(x):,}" if is_currency else f"{int(x):,}")
    )

    fig.update_traces(textposition="outside", marker_line_width=1.8,
                      marker_line_color="black", textfont=dict(color="black"))

    fig.update_layout(showlegend=False, height=650,
                      plot_bgcolor="white", paper_bgcolor="white",
                      margin=dict(t=140, b=200),
                      xaxis_title="Equipment", yaxis_title=y_label)

    fig.update_xaxes(showline=True, linewidth=2, linecolor="black", tickangle=-45)
    fig.update_yaxes(showline=True, linewidth=2, linecolor="black")

    fig.add_shape(type="rect", xref="paper", yref="paper",
                  x0=0, x1=1, y0=1.02, y1=1.12,
                  fillcolor=HEADER_BLUE, line_width=0)

    fig.add_annotation(
        x=0.5, y=1.07, xref="paper", yref="paper",
        text=f"<b>{title}</b>", showarrow=False,
        font=dict(color="white", size=15)
    )

    return fig

# ==========================================================
# DOWNLOAD
# ==========================================================
st.download_button("⬇️ Download Full Data (CSV)", df.to_csv(index=False), "procurement_data.csv")

# ==========================================================
# TABS → DEPARTMENTS
# ==========================================================
department_list = sorted(df["Department"].unique())
tabs = st.tabs(["Overview"] + department_list)

# OVERVIEW (UNCHANGED)
with tabs[0]:
    c1, c2 = st.columns(2)
    c1.plotly_chart(pie_chart(df, "Has Contract?", "Contract Coverage"), use_container_width=True)
    c2.plotly_chart(pie_chart(df, "Delivery Status", "Delivery Status Distribution"), use_container_width=True)

    st.plotly_chart(bar_chart(top10(df, "Unit_Price"), "Top 10 Equipment by Unit Price (USD)", "Unit_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Total_Price"), "Top 10 Equipment by Total Price (USD)", "Total_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Quantity"), "Top 10 Equipment by Quantity", "Quantity", "Quantity"), use_container_width=True)

# ==========================================================
# DEPARTMENT → SERVICE DRILL-DOWN
# ==========================================================
for i, dept in enumerate(department_list, start=1):
    with tabs[i]:
        dept_df = df[df["Department"] == dept]
        services = sorted(dept_df["Service"].unique())

        # Mini tabs only if meaningful
        if len(services) > 1:
            service_tabs = st.tabs(["All Services"] + services)
        else:
            service_tabs = [st.container()]

        for j, svc_tab in enumerate(service_tabs):
            with svc_tab:
                if len(services) > 1 and j > 0:
                    d = dept_df[dept_df["Service"] == services[j-1]]
                    title_suffix = f"{dept} – {services[j-1]}"
                else:
                    d = dept_df
                    title_suffix = dept

                c1, c2 = st.columns(2)
                c1.plotly_chart(pie_chart(d, "Has Contract?", f"Contract Coverage – {title_suffix}"), use_container_width=True)
                c2.plotly_chart(pie_chart(d, "Delivery Status", f"Delivery Status – {title_suffix}"), use_container_width=True)

                st.plotly_chart(bar_chart(top10(d, "Unit_Price"), f"Top 10 Unit Price – {title_suffix}", "Unit_Price", "USD", True), use_container_width=True)
                st.plotly_chart(bar_chart(top10(d, "Total_Price"), f"Top 10 Total Price – {title_suffix}", "Total_Price", "USD", True), use_container_width=True)
                st.plotly_chart(bar_chart(top10(d, "Quantity"), f"Top 10 Quantity – {title_suffix}", "Quantity", "Quantity"), use_container_width=True)
