import os
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
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
        # Linke Spalte: Buttons und Graphen
        html.Div([
            html.Div([
                html.Button("Letzte 24 Stunden", id="btn-24h", n_clicks=0, style={"margin": "5px"}),
                html.Button("Letzte Stunde", id="btn-1h", n_clicks=0, style={"margin": "5px"}),
                html.Button("Letzte 30 Minuten", id="btn-30m", n_clicks=0, style={"margin": "5px"}),
                html.Button("Letzte 10 Minuten", id="btn-10m", n_clicks=0, style={"margin": "5px"}),
            ], style={"textAlign": "center", "marginBottom": "20px"}),

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

    dcc.Store(id="time-range", data={"start": (datetime.now() - timedelta(hours=24)).isoformat()}),

    dcc.Interval(id="interval-update", interval=1000, n_intervals=0)
])

# Zeitraum-Callback: Aktualisiert den Zeitraum basierend auf den Buttons
@app.callback(
    Output("time-range", "data"),
    [Input("btn-24h", "n_clicks"),
     Input("btn-1h", "n_clicks"),
     Input("btn-30m", "n_clicks"),
     Input("btn-10m", "n_clicks")]
)
def update_time_range(btn_24h, btn_1h, btn_30m, btn_10m):
    now = datetime.now()
    ctx = dash.callback_context

    if not ctx.triggered:
        return {"start": (now - timedelta(hours=24)).isoformat()}

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "btn-24h":
        return {"start": (now - timedelta(hours=24)).isoformat()}
    elif button_id == "btn-1h":
        return {"start": (now - timedelta(hours=1)).isoformat()}
    elif button_id == "btn-30m":
        return {"start": (now - timedelta(minutes=30)).isoformat()}
    elif button_id == "btn-10m":
        return {"start": (now - timedelta(minutes=10)).isoformat()}

    return {"start": (now - timedelta(hours=24)).isoformat()}

# Graphen-Update-Callback: Aktualisiert die Graphen basierend auf dem Zeitraum
@app.callback(
    [Output("consumption-graph", "figure"),
     Output("feed-in-graph", "figure"),
     Output("net-usage-graph", "figure"),
     Output("combined-graph", "figure"),
     Output("total-consumption", "children"),
     Output("surplus-energy", "children"),
     Output("generated-energy", "children")],
    [Input("interval-update", "n_intervals")],
    [State("time-range", "data")]
)
def update_graphs(n_intervals, time_range):
    start_time = datetime.fromisoformat(time_range["start"])
    now = datetime.now()

    filtered_indices = [i for i, timestamp in enumerate(data_log["timestamps"]) if start_time <= timestamp <= now]

    if not filtered_indices:
        return {}, {}, {}, {}, "Stromverbrauch: 0.0000 kWh", "Verschenkter Strom: 0.0000 kWh", "Erzeugte Energie: 0.0000 kWh"

    timestamps = [data_log["timestamps"][i].strftime("%H:%M:%S") for i in filtered_indices]
    consumption = [data_log["consumption"][i] for i in filtered_indices]
    feed_in = [data_log["feed_in"][i] for i in filtered_indices]
    net_usage = [data_log["net_usage"][i] for i in filtered_indices]

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

    return consumption_fig, feed_in_fig, net_usage_fig, combined_fig, "Stromverbrauch: 0.0000 kWh", "Verschenkter Strom: 0.0000 kWh", "Erzeugte Energie: 0.0000 kWh"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)
