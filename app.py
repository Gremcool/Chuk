import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

# ----------------------------
# Load data (UNCHANGED)
# ----------------------------
df = pd.read_excel("procurement_data.xlsx")

# Ensure clean strings
df["Department"] = df["Department"].astype(str)
df["Service"] = df["Service"].astype(str)

# ----------------------------
# App
# ----------------------------
app = Dash(__name__, suppress_callback_exceptions=True)

# ----------------------------
# Layout
# ----------------------------
app.layout = html.Div([

    dcc.Tabs(id="main-tabs", value="overview", children=[

        # =========================
        # OVERVIEW TAB (UNCHANGED)
        # =========================
        dcc.Tab(label="Overview", value="overview", children=[
            html.Div("Overview content here")
        ]),

        # =========================
        # DEPARTMENTS TAB
        # =========================
        dcc.Tab(label="Departments", value="departments", children=[

            html.Div(style={"padding": "16px"}, children=[

                # ---- Department selector (already existed) ----
                dcc.Dropdown(
                    id="department-dropdown",
                    options=[
                        {"label": d, "value": d}
                        for d in sorted(df["Department"].unique())
                    ],
                    placeholder="Select Department",
                    clearable=False
                ),

                # ---- NEW: Service drill-down selector ----
                dcc.Dropdown(
                    id="service-dropdown",
                    placeholder="Drill down to Service (optional)",
                    clearable=True,
                    style={"marginTop": "10px"}
                ),

                # ---- Pie charts ----
                html.Div([
                    dcc.Graph(id="dept-pie-1"),
                    dcc.Graph(id="dept-pie-2")
                ], style={"display": "flex", "gap": "16px"}),

                # ---- Bar charts ----
                html.Div([
                    dcc.Graph(id="dept-bar-1"),
                    dcc.Graph(id="dept-bar-2")
                ], style={"marginTop": "20px"})

            ])
        ])
    ])
])

# ----------------------------
# Populate Service Dropdown
# ----------------------------
@app.callback(
    Output("service-dropdown", "options"),
    Input("department-dropdown", "value")
)
def update_service_dropdown(department):
    if not department:
        return []

    services = (
        df[df["Department"] == department]["Service"]
        .dropna()
        .unique()
    )

    return [{"label": s, "value": s} for s in sorted(services)]

# ----------------------------
# Update Charts (Department + Service Drill-down)
# ----------------------------
@app.callback(
    Output("dept-pie-1", "figure"),
    Output("dept-pie-2", "figure"),
    Output("dept-bar-1", "figure"),
    Output("dept-bar-2", "figure"),
    Input("department-dropdown", "value"),
    Input("service-dropdown", "value")
)
def update_department_charts(department, service):

    if not department:
        return {}, {}, {}, {}

    dff = df[df["Department"] == department]

    # ---- Drill-down applied ONLY if service selected ----
    if service:
        dff = dff[dff["Service"] == service]

    # ----------------------------
    # Pie charts (UNCHANGED STYLING)
    # ----------------------------
    pie1 = px.pie(
        dff,
        values="Amount",
        names="Category",
        title="Spend by Category"
    )
    pie1.update_layout(
        title_x=0.5,
        legend_title_text="",
        legend_font_size=14
    )

    pie2 = px.pie(
        dff,
        values="Amount",
        names="Supplier",
        title="Spend by Supplier"
    )
    pie2.update_layout(
        title_x=0.5,
        legend_title_text="",
        legend_font_size=14
    )

    # ----------------------------
    # Bar charts (COLORS + CENTERED TITLES PRESERVED)
    # ----------------------------
    bar1 = px.bar(
        dff.groupby("Month", as_index=False)["Amount"].sum(),
        x="Month",
        y="Amount",
        title="Monthly Spend Trend",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    bar1.update_layout(title_x=0.5)

    bar2 = px.bar(
        dff.groupby("Supplier", as_index=False)["Amount"].sum(),
        x="Supplier",
        y="Amount",
        title="Top Suppliers",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    bar2.update_layout(title_x=0.5)

    return pie1, pie2, bar1, bar2


# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    app.run_server(debug=True)
