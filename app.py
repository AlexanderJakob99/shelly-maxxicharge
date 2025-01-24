import os
import requests
import dash
from dash import dcc, html
from dash.dependencies import Output, Input, State
import json
from datetime import datetime, timedelta

# Dash-Anwendung erstellen
app = dash.Dash(__name__)
server = app.server

# Shelly Cloud API Details
AUTH_KEY = "MjIwNjI4dWlkEF704E100FDA0AE28EC1D8A8C551D70EDEA6568FB092A25C957D85FD6651DAEBD649BCF0A737EA47"
DEVICE_ID = "485519d94b97"
API_URL = f"https://shelly-98-eu.shelly.cloud/device/status?auth_key={AUTH_KEY}&id={DEVICE_ID}"

# Lokale Dateien zum Speichern der Daten
DATA_FILE = "data_log.json"
STATS_FILE = "statistics_log.json"

# In-Memory-Datenbank für die historischen Daten
data_log = {
    "timestamps": [],
    "consumption": [],
    "feed_in": [],
    "net_usage": []
}

# Statistiken für "Stromverbrauch", "Verschenkter Strom" und "Erzeugte Energie"
statistics_log = {
    "timestamps": [],
    "total_consumption": [],  # Stromverbrauch in kWh
    "surplus_energy": [],  # Verschenkter Strom in kWh
    "generated_energy": []  # Erzeugte Energie in kWh
}

# Variablen zur Berechnung der Werte
total_consumption = 0  # in Wattsekunden
surplus_energy = 0  # in Wattsekunden
generated_energy = 0  # in Wattsekunden


# Funktion, um Daten von der Shelly Cloud API abzurufen
def get_shelly_data():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()

            # Extrahieren der Leistungsdaten aus 'emeters'
            if "data" in data and "device_status" in data["data"] and "emeters" in data["data"]["device_status"]:
                emeters = data["data"]["device_status"]["emeters"]
                power_values = [float(phase.get("power", 0)) for phase in emeters]
                return power_values
            else:
                return [0.0, 0.0, 0.0]
        else:
            return [0.0, 0.0, 0.0]
    except Exception:
        return [0.0, 0.0, 0.0]


# Layout der App
app.layout = html.Div([
    html.H1("Shelly 3EM Dashboard", style={"textAlign": "center"}),

    html.Div([
        # Linke Spalte: Graphen und Buttons
        html.Div([
            # Buttons für die Zeiträume
            html.Div([
                html.Button("Letzte 24 Stunden", id="btn-24h", n_clicks=0, style={"margin": "5px"}),
                html.Button("Letzte Stunde", id="btn-1h", n_clicks=0, style={"margin": "5px"}),
                html.Button("Letzte 30 Minuten", id="btn-30m", n_clicks=0, style={"margin": "5px"}),
                html.Button("Letzte 10 Minuten", id="btn-10m", n_clicks=0, style={"margin": "5px"})
            ], style={"textAlign": "center", "marginBottom": "20px"}),

            # Graphen
            dcc.Graph(id="consumption-graph", config={"scrollZoom": True}),
            dcc.Graph(id="feed-in-graph", config={"scrollZoom": True}),
            dcc.Graph(id="net-usage-graph", config={"scrollZoom": True}),
            dcc.Graph(
                id="combined-graph",
                config={"scrollZoom": True},
                style={"height": "60vh"}
            ),
        ], style={"width": "65%", "display": "inline-block", "verticalAlign": "top"}),

        # Rechte Spalte: Statistiken
        html.Div([
            html.H2("Statistiken", style={"textAlign": "center"}),

            html.Div(id="total-consumption", style={"fontSize": "20px", "marginBottom": "20px"}),
            html.Div(id="surplus-energy", style={"fontSize": "20px", "marginBottom": "20px"}),
            html.Div(id="generated-energy", style={"fontSize": "20px", "marginBottom": "20px"}),
        ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top", "padding": "20px"}),
    ]),

    # Store für den aktuellen Zeitraum
    dcc.Store(id="time-range", data={"start": datetime.now() - timedelta(hours=24)}),

    dcc.Interval(
        id="interval-update",
        interval=1000,  # Alle 1 Sekunde aktualisieren
        n_intervals=0
    )
])


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
        return {"start": now - timedelta(hours=24)}

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "btn-24h":
        return {"start": now - timedelta(hours=24)}
    elif button_id == "btn-1h":
        return {"start": now - timedelta(hours=1)}
    elif button_id == "btn-30m":
        return {"start": now - timedelta(minutes=30)}
    elif button_id == "btn-10m":
        return {"start": now - timedelta(minutes=10)}

    return {"start": now - timedelta(hours=24)}


@app.callback(
    [Output("consumption-graph", "figure"),
     Output("feed-in-graph", "figure"),
     Output("net-usage-graph", "figure"),
     Output("combined-graph", "figure")],
    [Input("interval-update", "n_intervals"),
     Input("time-range", "data")]
)
def update_graphs(n_intervals, time_range):
    start_time = datetime.fromisoformat(time_range["start"])
    now = datetime.now()

    # Filter Daten basierend auf dem ausgewählten Zeitraum
    filtered_indices = [i for i, timestamp in enumerate(data_log["timestamps"]) if start_time <= timestamp <= now]

    timestamps = [data_log["timestamps"][i].strftime("%H:%M:%S") for i in filtered_indices]
    consumption = [data_log["consumption"][i] for i in filtered_indices]
    feed_in = [data_log["feed_in"][i] for i in filtered_indices]
    net_usage = [data_log["net_usage"][i] for i in filtered_indices]

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
            "legend": {"orientation": "h", "x": 0.5, "xanchor": "center"},  # Legende unten
            "uirevision": "constant"  # Zustand beibehalten
        }
    }

    return consumption_fig, feed_in_fig, net_usage_fig, combined_fig


# Anwendung starten
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)
