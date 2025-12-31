import streamlit as st
import pandas as pd
import plotly.express as px
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
# LOAD DATA (SAFE FOR STREAMLIT CLOUD)
# ==========================================================
@st.cache_data(ttl=30)
def load_data():
    r = requests.get(GOOGLE_SHEET_CSV)
    r.raise_for_status()
    df_raw = pd.read_csv(StringIO(r.text))

    df = df_raw[
        ["Equipment name", "Service", "QTY Requested", "Unit Price RWF"]
    ].copy()

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
# SEARCH (ONLY FILTER ALLOWED)
# ==========================================================
search = st.text_input("🔍 Search Equipment", placeholder="Type equipment name…")

df_view = df.copy()
if search:
    df_view = df_view[df_view["Equipment"].str.contains(search, case=False, na=False)]

# ==========================================================
# WRAP LABELS (EXACT SAME AS HTML)
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

df_view["Equipment_wrapped"] = df_view["Equipment"].apply(wrap_text)

# ==========================================================
# TOP 10 LOGIC (UNCHANGED)
# ==========================================================
def top10(df_in, metric):
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates(subset=["Equipment_wrapped"])
        df_grouped = df_unique.groupby("Equipment_wrapped", as_index=False)[metric].max()
    else:
        df_grouped = df_in.groupby("Equipment_wrapped", as_index=False)[metric].sum()

    return df_grouped.sort_values(metric, ascending=False).head(10)

# ==========================================================
# BAR CHART (HTML-FAITHFUL)
# ==========================================================
def bar_chart(df_in, title, y_col, y_label, is_currency=False):
    fig = px.bar(
        df_in,
        x="Equipment_wrapped",
        y=y_col,
        color="Equipment_wrapped",
        color_discrete_sequence=px.colors.qualitative.Set3,
        text=df_in[y_col].apply(
            lambda x: f"${int(x):,}" if is_currency else f"{int(x):,}"
        )
    )

    fig.update_traces(textposition="outside")
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=650,
        margin=dict(t=95, b=200),
        xaxis_title="Equipment",
        yaxis_title=y_label
    )
    fig.update_xaxes(tickangle=-45)

    fig.add_shape(
        type="rect",
        xref="paper", yref="paper",
        x0=0, x1=1,
        y0=1.05, y1=1.12,
        fillcolor=HEADER_BLUE,
        line_width=0
    )

    fig.add_annotation(
        x=0.5, y=1.085,
        xref="paper", yref="paper",
        text=f"<b>{title}</b>",
        showarrow=False,
        font=dict(color="white", size=15)
    )

    return fig

# ==========================================================
# HEADER
# ==========================================================
st.markdown(
    f"<h1 style='text-align:center;color:{HEADER_BLUE};'>Procurement Analysis Dashboard (USD)</h1>",
    unsafe_allow_html=True
)

# ==========================================================
# KPIs (ALL DATA – SAME AS HTML)
# ==========================================================
k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Budget", f"${int(df_view['Total_Price'].sum()):,}")
k2.metric("Total Quantity", f"{int(df_view['Quantity'].sum()):,}")
k3.metric("Services", df_view["Service"].nunique())
k4.metric("Equipment Items", df_view["Equipment"].nunique())

# ==========================================================
# TABS (EXACT SERVICE TABS LIKE EXCEL)
# ==========================================================
services = sorted(df["Service"].unique())
tabs = st.tabs(["Overview"] + services)

# OVERVIEW TAB
with tabs[0]:
    st.plotly_chart(bar_chart(top10(df_view, "Unit_Price"),
                              "Top 10 Equipment by Unit Price (USD)",
                              "Unit_Price", "USD", True),
                    use_container_width=True)

    st.plotly_chart(bar_chart(top10(df_view, "Total_Price"),
                              "Top 10 Equipment by Total Price (USD)",
                              "Total_Price", "USD", True),
                    use_container_width=True)

    st.plotly_chart(bar_chart(top10(df_view, "Quantity"),
                              "Top 10 Equipment by Quantity",
                              "Quantity", "Quantity"),
                    use_container_width=True)

# SERVICE TABS
for i, s in enumerate(services, start=1):
    with tabs[i]:
        d = df_view[df_view["Service"] == s]

        if d.empty:
            st.info("No data available")
            continue

        st.plotly_chart(bar_chart(top10(d, "Unit_Price"),
                                  f"Top 10 Unit Price – {s}",
                                  "Unit_Price", "USD", True),
                        use_container_width=True)

        st.plotly_chart(bar_chart(top10(d, "Total_Price"),
                                  f"Top 10 Total Price – {s}",
                                  "Total_Price", "USD", True),
                        use_container_width=True)

        st.plotly_chart(bar_chart(top10(d, "Quantity"),
                                  f"Top 10 Quantity – {s}",
                                  "Quantity", "Quantity"),
                        use_container_width=True)
