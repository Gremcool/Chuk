import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================================
# CONFIG
# ==========================================================
st.set_page_config(page_title="Procurement Dashboard", layout="wide")
USD_RATE = 1454
HEADER_BLUE = "#0D47A1"
GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTzHV5uRT-b-3-0uBub083j6tOTdPU7NFK_ESyMKuT0pYNwMaWHFNy9uU1u8miMOQ/pub?gid=1002181482&single=true&output=csv"

# ==========================================================
# LOAD DATA
# ==========================================================
@st.cache_data(ttl=60)
def load_data():
    df_raw = pd.read_csv(GOOGLE_SHEET_CSV)
    df = df_raw[["Equipment name", "Service", "QTY Requested", "Unit Price RWF"]].copy()
    df.columns = ["Equipment", "Service", "Quantity", "Unit_Price_RWF"]

    df["Equipment"] = df["Equipment"].astype(str).str.strip()
    df["Service"] = df["Service"].astype(str).str.strip()
    df.loc[df["Service"].isin(["", "nan", "None"]), "Service"] = "Unknown"

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    df["Unit_Price_RWF"] = pd.to_numeric(df["Unit_Price_RWF"], errors="coerce").fillna(0)

    # Total price logic exactly like your HTML code
    df["Unit_Price"] = df["Unit_Price_RWF"] / USD_RATE
    df["Total_Price"] = (df["Unit_Price_RWF"] * df["Quantity"]) / USD_RATE

    # Label wrapping for bar charts
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
    return df

df = load_data()

# ==========================================================
# KPI VALUES
# ==========================================================
total_budget = int((df["Unit_Price_RWF"] * df["Quantity"]).sum() / USD_RATE)
total_qty = int(df["Quantity"].sum())
num_services = df["Service"].nunique()
num_items = df["Equipment"].nunique()

# ==========================================================
# TOP 10 FUNCTION
# ==========================================================
def top10(df_in, metric):
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates(subset=["Equipment_wrapped"])
        df_grouped = df_unique.groupby("Equipment_wrapped", as_index=False)[metric].max()
    else:
        df_grouped = df_in.groupby("Equipment_wrapped", as_index=False)[metric].sum()
    df_grouped = df_grouped[df_grouped[metric] > 0]
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
card_style = f"background:white;border-left:6px solid {HEADER_BLUE};border-radius:12px;padding:14px 16px;"
c1.markdown(f"<div style='{card_style}'><div style='font-size:13px;color:#546E7A;font-weight:600'>Total Budget</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>${total_budget:,}</div></div>", unsafe_allow_html=True)
c2.markdown(f"<div style='{card_style}'><div style='font-size:13px;color:#546E7A;font-weight:600'>Total Quantity</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>{total_qty:,}</div></div>", unsafe_allow_html=True)
c3.markdown(f"<div style='{card_style}'><div style='font-size:13px;color:#546E7A;font-weight:600'>Services</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>{num_services}</div></div>", unsafe_allow_html=True)
c4.markdown(f"<div style='{card_style}'><div style='font-size:13px;color:#546E7A;font-weight:600'>Equipment Items</div><div style='font-size:22px;font-weight:700;color:{HEADER_BLUE}'>{num_items}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ==========================================================
# SERVICE TABS (TWO ROWS)
# ==========================================================
all_services = ["Overview"] + sorted(df["Service"].unique())
num_cols = 11  # 22 services -> 2 rows
rows = [all_services[i:i+num_cols] for i in range(0, len(all_services), num_cols)]

tab_choice = None
for row in rows:
    cols = st.columns(len(row))
    for i, svc in enumerate(row):
        if cols[i].button(svc):
            tab_choice = svc

if tab_choice is None:
    tab_choice = "Overview"

# ==========================================================
# DISPLAY TAB CONTENT
# ==========================================================
if tab_choice == "Overview":
    st.plotly_chart(bar_chart(top10(df, "Unit_Price"), "Top 10 Equipment by Unit Price (USD)", "Unit_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Total_Price"), "Top 10 Equipment by Total Price (USD)", "Total_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(df, "Quantity"), "Top 10 Equipment by Quantity", "Quantity", "Quantity", False), use_container_width=True)

    service_budget = df.groupby("Service", as_index=False)["Total_Price"].sum().sort_values("Total_Price", ascending=False)
    service_budget.loc[len(service_budget)] = ["TOTAL", service_budget["Total_Price"].sum()]
    service_budget["Total Budget (USD)"] = service_budget["Total_Price"].apply(lambda x: f"${int(x):,}")
    st.subheader("Service Budget Summary")
    st.dataframe(service_budget[["Service", "Total Budget (USD)"]], use_container_width=True, hide_index=True)

else:
    d = df[df["Service"] == tab_choice]
    st.plotly_chart(bar_chart(top10(d, "Unit_Price"), f"Top 10 Unit Price – {tab_choice}", "Unit_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(d, "Total_Price"), f"Top 10 Total Price – {tab_choice}", "Total_Price", "USD", True), use_container_width=True)
    st.plotly_chart(bar_chart(top10(d, "Quantity"), f"Top 10 Quantity – {tab_choice}", "Quantity", "Quantity", False), use_container_width=True)
