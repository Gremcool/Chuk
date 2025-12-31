import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================================
# CONFIG
# ==========================================================
st.set_page_config(page_title="Procurement Dashboard", layout="wide")

USD_RATE = 1454
HEADER_BLUE = "#0D47A1"

INPUT_FILE = "CHUK.xlsx"   # MUST be same file as HTML version

# ==========================================================
# LOAD DATA (NO CACHING — FOR CORRECTNESS)
# ==========================================================
df_raw = pd.read_excel(INPUT_FILE)

df = df_raw[
    ["Equipment name", "Service", "QTY Requested", "Unit Price RWF"]
].copy()

df.columns = ["Equipment", "Service", "Quantity", "Unit_Price_RWF"]

# ==========================================================
# CLEAN DATA (IDENTICAL)
# ==========================================================
df["Equipment"] = df["Equipment"].astype(str).str.strip()
df["Service"] = df["Service"].astype(str).str.strip()
df.loc[df["Service"].isin(["", "nan", "None"]), "Service"] = "Unknown"

df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
df["Unit_Price_RWF"] = pd.to_numeric(df["Unit_Price_RWF"], errors="coerce").fillna(0)

# ==========================================================
# CURRENCY (IDENTICAL)
# ==========================================================
df["Unit_Price"] = df["Unit_Price_RWF"] / USD_RATE
df["Total_Price"] = df["Unit_Price"] * df["Quantity"]

# ==========================================================
# KPI VALUES (IDENTICAL — FULL DF)
# ==========================================================
total_budget = int(df["Total_Price"].sum())
total_qty = int(df["Quantity"].sum())
num_services = df["Service"].nunique()
num_items = df["Equipment"].nunique()

# 🔴 DEBUG GUARD — YOU EXPECT THIS
# st.write("DEBUG TOTAL:", total_budget)

# ==========================================================
# LABEL WRAP (IDENTICAL)
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
# TOP 10 LOGIC (CRITICAL — IDENTICAL)
# ==========================================================
def top10(df_in, metric):
    if metric == "Unit_Price":
        df_unique = df_in.drop_duplicates(subset=["Equipment_wrapped"])
        df_grouped = (
            df_unique
            .groupby("Equipment_wrapped", as_index=False)[metric]
            .max()
        )
    else:
        df_grouped = (
            df_in
            .groupby("Equipment_wrapped", as_index=False)[metric]
            .sum()
        )

    return df_grouped.sort_values(metric, ascending=False).head(10)

# ==========================================================
# BAR CHART (NO LOGIC CHANGE)
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
        yaxis_title=y_label,
        title=dict(
            text=f"<b>{title}</b>",
            x=0.5,
            font=dict(color="white", size=15),
            bgcolor=HEADER_BLUE
        )
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
# KPI ROW
# ==========================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Budget", f"${total_budget:,}")
c2.metric("Total Quantity", f"{total_qty:,}")
c3.metric("Services", num_services)
c4.metric("Equipment Items", num_items)

st.markdown("---")

# ==========================================================
# TABS (ALL SERVICES — WRAPS TO MULTIPLE ROWS)
# ==========================================================
services = ["Overview"] + sorted(df["Service"].unique())
tabs = st.tabs(services)

# ==========================================================
# OVERVIEW TAB
# ==========================================================
with tabs[0]:
    st.plotly_chart(
        bar_chart(top10(df, "Unit_Price"),
                  "Top 10 Equipment by Unit Price (USD)",
                  "Unit_Price", "USD", True),
        use_container_width=True
    )

    st.plotly_chart(
        bar_chart(top10(df, "Total_Price"),
                  "Top 10 Equipment by Total Price (USD)",
                  "Total_Price", "USD", True),
        use_container_width=True
    )

    st.plotly_chart(
        bar_chart(top10(df, "Quantity"),
                  "Top 10 Equipment by Quantity",
                  "Quantity", "Quantity", False),
        use_container_width=True
    )

    service_budget = (
        df.groupby("Service", as_index=False)["Total_Price"]
        .sum()
        .sort_values("Total_Price", ascending=False)
    )

    service_budget.loc[len(service_budget)] = [
        "TOTAL",
        service_budget["Total_Price"].sum()
    ]

    service_budget["Total Budget (USD)"] = service_budget["Total_Price"].apply(
        lambda x: f"${int(x):,}"
    )

    st.subheader("Service Budget Summary")
    st.dataframe(
        service_budget[["Service", "Total Budget (USD)"]],
        use_container_width=True,
        hide_index=True
    )

# ==========================================================
# SERVICE TABS
# ==========================================================
for i, s in enumerate(services[1:], start=1):
    with tabs[i]:
        d = df[df["Service"] == s]

        st.plotly_chart(
            bar_chart(top10(d, "Unit_Price"),
                      f"Top 10 Unit Price – {s}",
                      "Unit_Price", "USD", True),
            use_container_width=True
        )

        st.plotly_chart(
            bar_chart(top10(d, "Total_Price"),
                      f"Top 10 Total Price – {s}",
                      "Total_Price", "USD", True),
            use_container_width=True
        )

        st.plotly_chart(
            bar_chart(top10(d, "Quantity"),
                      f"Top 10 Quantity – {s}",
                      "Quantity", "Quantity", False),
            use_container_width=True
        )
