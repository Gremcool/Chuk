import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================================
# CONFIG
# ==========================================================
st.set_page_config(page_title="Procurement Dashboard", layout="wide")
USD_RATE = 1454
HEADER_BLUE = "#0D47A1"
INPUT_FILE = "CHUK.xlsx"  # Make sure it's the same file as your HTML script

# ==========================================================
# LOAD DATA
# ==========================================================
df_raw = pd.read_excel(INPUT_FILE)
df = df_raw[["Equipment name", "Service", "QTY Requested", "Unit Price RWF"]].copy()
df.columns = ["Equipment", "Service", "Quantity", "Unit_Price_RWF"]

# ==========================================================
# CLEAN DATA
# ==========================================================
df["Equipment"] = df["Equipment"].astype(str).str.strip()
df["Service"] = df["Service"].astype(str).str.strip()
df.loc[df["Service"].isin(["", "nan", "None"]), "Service"] = "Unknown"
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
df["Unit_Price_RWF"] = pd.to_numeric(df["Unit_Price_RWF"], errors="coerce").fillna(0)

# ==========================================================
# CURRENCY CORRECTED
# ==========================================================
df["Total_Price"] = df["Unit_Price_RWF"] * df["Quantity"] / USD_RATE
df["Unit_Price"] = df["Unit_Price_RWF"] / USD_RATE

# ==========================================================
# KPI VALUES
# ==========================================================
total_budget = int((df["Unit_Price_RWF"] * df["Quantity"]).sum() / USD_RATE)
total_qty = int(df["Quantity"].sum())
num_services = df["Service"].nunique()
num_items = df["Equipment"].nunique()

# ==========================================================
# LABEL WRAP
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
# TOP 10 LOGIC
# ==========================================================
def top10(df_in, metric):
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates(subset=["Equipment_wrapped"])
        df_grouped = df_unique.groupby("Equipment_wrapped", as_index=False)[metric].max()
    else:
        df_grouped = df_in.groupby("Equipment_wrapped", as_index=False)[metric].sum()
    return df_grouped.sort_values(metric, ascending=False).head(10)

# ==========================================================
# BAR CHART FUNCTION
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
        margin=dict(t=95, b=200),
        xaxis_title="Equipment",
        yaxis_title=y_label
    )
    fig.update_xaxes(tickangle=-45)
    return fig

# ==========================================================
# HEADER
# ==========================================================
st.markdown(
    f"<h1 style='text-align:center;color:{HEADER_BLUE};'>Procurement Analysis Dashboard (USD)</h1>",
    unsafe_allow_html=True
)

# ==========================================================
# KPI CARDS
# ==========================================================
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f"<div style='background:white;border-left:6px solid {HEADER_BLUE};border-radius:12px;padding:14px 16px;'><div style='font-size:13px;color:#546E7A;font-weight:600'>Total Budget</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>${total_budget:,}</div></div>", unsafe_allow_html=True)
c2.markdown(f"<div style='background:white;border-left:6px solid {HEADER_BLUE};border-radius:12px;padding:14px 16px;'><div style='font-size:13px;color:#546E7A;font-weight:600'>Total Quantity</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>{total_qty:,}</div></div>", unsafe_allow_html=True)
c3.markdown(f"<div style='background:white;border-left:6px solid {HEADER_BLUE};border-radius:12px;padding:14px 16px;'><div style='font-size:13px;color:#546E7A;font-weight:600'>Services</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>{num_services}</div></div>", unsafe_allow_html=True)
c4.markdown(f"<div style='background:white;border-left:6px solid {HEADER_BLUE};border-radius:12px;padding:14px 16px;'><div style='font-size:13px;color:#546E7A;font-weight:600'>Equipment Items</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>{num_items}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================================
# TABS (ALL SERVICES VISIBLE IN 2 ROWS)
# ==========================================================
services = ["Overview"] + sorted(df["Service"].unique())
rows_needed = 2
tabs_per_row = (len(services) + rows_needed - 1) // rows_needed

tabs_layout = []
for i in range(rows_needed):
    start = i * tabs_per_row
    end = start + tabs_per_row
    tabs_layout.append(services[start:end])

# Streamlit has only one st.tabs(), so combine two rows visually using columns
tab_objects = []
for row in tabs_layout:
    cols = st.columns(len(row))
    for i, s in enumerate(row):
        tab_objects.append((cols[i], s))

# ==========================================================
# OVERVIEW TAB
# ==========================================================
overview_idx = services.index("Overview")
col, tab_name = tab_objects[overview_idx]
with col:
    st.subheader(tab_name)
    st.plotly_chart(bar_chart(top10(df, "Unit_Price"), "Top 10 Equipment by Unit Price (USD)", "Unit_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Total_Price"), "Top 10 Equipment by Total Price (USD)", "Total_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Quantity"), "Top 10 Equipment by Quantity", "Quantity", "Quantity", False), use_container_width=True)

    service_budget = df.groupby("Service", as_index=False)["Total_Price"].sum().sort_values("Total_Price", ascending=False)
    service_budget.loc[len(service_budget)] = ["TOTAL", service_budget["Total_Price"].sum()]
    service_budget["Total Budget (USD)"] = service_budget["Total_Price"].apply(lambda x: f"${int(x):,}")
    st.subheader("Service Budget Summary")
    st.dataframe(service_budget[["Service", "Total Budget (USD)"]], use_container_width=True, hide_index=True)

# ==========================================================
# SERVICE TABS
# ==========================================================
for i, s in enumerate(services[1:], start=1):
    col, tab_name = tab_objects[i]
    with col:
        st.subheader(tab_name)
        d = df[df["Service"] == s]
        st.plotly_chart(bar_chart(top10(d, "Unit_Price"), f"Top 10 Unit Price – {s}", "Unit_Price", "USD", True), use_container_width=True)
        st.plotly_chart(bar_chart(top10(d, "Total_Price"), f"Top 10 Total Price – {s}", "Total_Price", "USD", True), use_container_width=True)
        st.plotly_chart(bar_chart(top10(d, "Quantity"), f"Top 10 Quantity – {s}", "Quantity", "Quantity", False), use_container_width=True)
