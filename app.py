import os
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
from datetime import datetime, timedelta

# Dash-Anwendung erstellen
app = dash.Dash(__name__)
server = app.server

# Beispiel-Daten
data_log = {
    "timestamps": [datetime.now() - timedelta(minutes=i) for i in range(120)],
    "consumption": [100 + i % 10 for i in range(120)],
    "feed_in": [50 - i % 5 for i in range(120)],
    "net_usage": [50 + i % 7 for i in range(120)],
}

# Layout der App
app.layout = html.Div([
    html.H1("Shelly 3EM Dashboard", style={"textAlign": "center"}),

    html.Div([
        # Linke Spalte: Graphen
        html.Div([
            dcc.Graph(id="consumption-graph", config={"scrollZoom": True}),
            dcc.Graph(id="feed-in-graph", config={"scrollZoom": True}),
            dcc.Graph(id="net-usage-graph", config={"scrollZoom": True}),
            dcc.Graph(id="combined-graph", config={"scrollZoom": True}),
        ], style={"width": "65%", "display": "inline-block", "verticalAlign": "top"}),

        # Rechte Spalte: Statistiken
        html.Div([
            html.H2("Statistiken", style={"textAlign": "center"}),

            html.Div(id="total-consumption", style={"fontSize": "20px", "marginBottom": "20px"}),
            html.Div(id="surplus-energy", style={"fontSize": "20px", "marginBottom": "20px"}),
            html.Div(id="generated-energy", style={"fontSize": "20px", "marginBottom": "20px"}),
        ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top", "padding": "20px"}),
    ]),

    dcc.Interval(id="interval-update", interval=1000, n_intervals=0)
])

# Graphen-Update-Callback: Aktualisiert die Graphen basierend auf den vollständigen Daten
@app.callback(
    [Output("consumption-graph", "figure"),
     Output("feed-in-graph", "figure"),
     Output("net-usage-graph", "figure"),
     Output("combined-graph", "figure"),
     Output("total-consumption", "children"),
     Output("surplus-energy", "children"),
     Output("generated-energy", "children")],
    [Input("interval-update", "n_intervals")]
)
def update_graphs(n_intervals):
    timestamps = [timestamp.strftime("%H:%M:%S") for timestamp in data_log["timestamps"]]
    consumption = data_log["consumption"]
    feed_in = data_log["feed_in"]
    net_usage = data_log["net_usage"]

    # Einzelne Graphen
    consumption_fig = {
        "data": [{"x": timestamps, "y": consumption, "type": "scatter", "mode": "lines", "name": "Verbrauch", "line": {"shape": "spline", "color": "red"}}],
        "layout": {"title": "Stromverbrauch (W)", "uirevision": "constant"}
    }

    feed_in_fig = {
        "data": [{"x": timestamps, "y": feed_in, "type": "scatter", "mode": "lines", "name": "Einspeisung", "line": {"shape": "spline", "color": "green"}}],
        "layout": {"title": "Einspeisung (W)", "uirevision": "constant"}
    }

    net_usage_fig = {
        "data": [{"x": timestamps, "y": net_usage, "type": "scatter", "mode": "lines", "name": "Netzbezug", "line": {"shape": "spline", "color": "blue"}}],
        "layout": {"title": "Netzbezug (W)", "uirevision": "constant"}
    }

    # Kombinierter Graph
    combined_fig = {
        "data": [
            {"x": timestamps, "y": consumption, "type": "scatter", "mode": "lines", "name": "Verbrauch", "line": {"shape": "spline", "color": "red"}},
            {"x": timestamps, "y": feed_in, "type": "scatter", "mode": "lines", "name": "Einspeisung", "line": {"shape": "spline", "color": "green"}},
            {"x": timestamps, "y": net_usage, "type": "scatter", "mode": "lines", "name": "Netzbezug", "line": {"shape": "spline", "color": "blue"}}
        ],
        "layout": {
            "title": "Kombinierter Graph: Verbrauch, Einspeisung und Netzbezug",
            "xaxis": {"title": "Zeit"},
            "yaxis": {"title": "Leistung (W)"},
            "legend": {"orientation": "h", "x": 0.5, "xanchor": "center"},
            "uirevision": "constant"
        }
    }

    # Beispielwerte für Statistiken
    total_consumption = sum(consumption) / 1000  # kWh
    surplus_energy = sum(feed_in) / 1000  # kWh
    generated_energy = sum(net_usage) / 1000  # kWh

    return (
        consumption_fig,
        feed_in_fig,
        net_usage_fig,
        combined_fig,
        f"Stromverbrauch: {total_consumption:.4f} kWh",
        f"Verschenkter Strom: {surplus_energy:.4f} kWh",
        f"Erzeugte Energie: {generated_energy:.4f} kWh"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)
