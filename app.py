import os
import requests
import dash
from dash import dcc, html
from dash.dependencies import Output, Input
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


# Berechnung von Verbrauch, Einspeisung und Netzbezug
def calculate_energy(power_values):
    power_values = [float(p) for p in power_values]
    consumption = sum([p for p in power_values if p > 0])  # Nur positive Werte (Stromverbrauch)
    feed_in = abs(sum([p for p in power_values if p < 0]))  # Nur negative Werte (Einspeisung)
    net_usage = consumption - feed_in
    return consumption, feed_in, net_usage  # Stromverbrauch bleibt unverändert


# Funktion, um Daten auf die letzten 24 Stunden zu beschränken
def trim_data_log():
    global data_log, statistics_log
    now = datetime.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Trim Data Log
    valid_indices = [i for i, timestamp in enumerate(data_log["timestamps"]) if timestamp >= twenty_four_hours_ago]
    data_log["timestamps"] = [data_log["timestamps"][i] for i in valid_indices]
    data_log["consumption"] = [data_log["consumption"][i] for i in valid_indices]
    data_log["feed_in"] = [data_log["feed_in"][i] for i in valid_indices]
    data_log["net_usage"] = [data_log["net_usage"][i] for i in valid_indices]

    # Trim Statistics Log
    valid_indices_stats = [i for i, timestamp in enumerate(statistics_log["timestamps"]) if timestamp >= twenty_four_hours_ago]
    statistics_log["timestamps"] = [statistics_log["timestamps"][i] for i in valid_indices_stats]
    statistics_log["total_consumption"] = [statistics_log["total_consumption"][i] for i in valid_indices_stats]
    statistics_log["surplus_energy"] = [statistics_log["surplus_energy"][i] for i in valid_indices_stats]
    statistics_log["generated_energy"] = [statistics_log["generated_energy"][i] for i in valid_indices_stats]


# Funktion, um die Daten in Dateien zu speichern
def save_data_log():
    with open(DATA_FILE, "w") as file:
        json.dump(data_log, file, default=str)


def save_statistics_log():
    with open(STATS_FILE, "w") as file:
        json.dump(statistics_log, file, default=str)


# Funktion, um die Daten aus Dateien zu laden
def load_data_log():
    global data_log
    try:
        with open(DATA_FILE, "r") as file:
            loaded_data = json.load(file)
            data_log["timestamps"] = [datetime.fromisoformat(ts) for ts in loaded_data["timestamps"]]
            data_log["consumption"] = loaded_data["consumption"]
            data_log["feed_in"] = loaded_data["feed_in"]
            data_log["net_usage"] = loaded_data["net_usage"]
    except FileNotFoundError:
        pass


def load_statistics_log():
    global statistics_log
    try:
        with open(STATS_FILE, "r") as file:
            loaded_stats = json.load(file)
            statistics_log["timestamps"] = [datetime.fromisoformat(ts) for ts in loaded_stats["timestamps"]]
            statistics_log["total_consumption"] = loaded_stats["total_consumption"]
            statistics_log["surplus_energy"] = loaded_stats["surplus_energy"]
            statistics_log["generated_energy"] = loaded_stats["generated_energy"]
    except FileNotFoundError:
        pass


# Layout der App
app.layout = html.Div([
    html.H1("Shelly 3EM Dashboard", style={"textAlign": "center"}),

    html.Div([
        # Linke Spalte: Einzelne Graphen und kombinierter Graph
        html.Div([
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

    dcc.Interval(
        id="interval-update",
        interval=1000,  # Alle 1 Sekunde aktualisieren
        n_intervals=0
    )
])


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
    global data_log, statistics_log, total_consumption, surplus_energy, generated_energy

    # Daten abrufen
    power_values = get_shelly_data()
    if not power_values or all(v == 0 for v in power_values):
        return {}, {}, {}, {}, "Stromverbrauch: 0.0000 kWh", "Verschenkter Strom: 0.0000 kWh", "Erzeugte Energie: 0.0000 kWh"

    consumption, feed_in, net_usage = calculate_energy(power_values)
    current_time = datetime.now()

    # Daten in den Speicher schreiben
    data_log["timestamps"].append(current_time)
    data_log["consumption"].append(consumption)
    data_log["feed_in"].append(feed_in)
    data_log["net_usage"].append(net_usage)

    # Berechnung der Werte in Wattsekunden
    total_consumption += consumption
    if net_usage < 0:
        surplus_energy += abs(net_usage)
    generated_energy += feed_in

    # Umrechnung in kWh
    total_consumption_kwh = total_consumption / 3600000
    surplus_energy_kwh = surplus_energy / 3600000
    generated_energy_kwh = generated_energy / 3600000

    statistics_log["timestamps"].append(current_time)
    statistics_log["total_consumption"].append(total_consumption_kwh)
    statistics_log["surplus_energy"].append(surplus_energy_kwh)
    statistics_log["generated_energy"].append(generated_energy_kwh)

    # Daten trimmen und speichern
    trim_data_log()
    save_data_log()
    save_statistics_log()

    # Einzelne Graphen
    timestamps = [t.strftime("%H:%M:%S") for t in data_log["timestamps"]]
    consumption_fig = {
        "data": [{"x": timestamps, "y": data_log["consumption"], "type": "scatter", "mode": "lines", "name": "Verbrauch", "line": {"shape": "spline", "color": "red"}}],
        "layout": {"title": "Stromverbrauch (W)", "uirevision": "constant"}
    }

    feed_in_fig = {
        "data": [{"x": timestamps, "y": data_log["feed_in"], "type": "scatter", "mode": "lines", "name": "Einspeisung", "line": {"shape": "spline", "color": "green"}}],
        "layout": {"title": "Einspeisung (W)", "uirevision": "constant"}
    }

    net_usage_fig = {
        "data": [{"x": timestamps, "y": data_log["net_usage"], "type": "scatter", "mode": "lines", "name": "Netzbezug", "line": {"shape": "spline", "color": "blue"}}],
        "layout": {"title": "Netzbezug (W)", "uirevision": "constant"}
    }

    # Kombinierter Graph
    combined_fig = {
        "data": [
            {"x": timestamps, "y": data_log["consumption"], "type": "scatter", "mode": "lines", "name": "Verbrauch", "line": {"shape": "spline", "color": "red"}},
            {"x": timestamps, "y": data_log["feed_in"], "type": "scatter", "mode": "lines", "name": "Einspeisung", "line": {"shape": "spline", "color": "green"}},
            {"x": timestamps, "y": data_log["net_usage"], "type": "scatter", "mode": "lines", "name": "Netzbezug", "line": {"shape": "spline", "color": "blue"}}
        ],
        "layout": {
            "title": "Kombinierter Graph: Verbrauch, Einspeisung und Netzbezug",
            "xaxis": {"title": "Zeit"},
            "yaxis": {"title": "Leistung (W)"},
            "legend": {"orientation": "h", "x": 0.5, "xanchor": "center"},  # Legende unten
            "uirevision": "constant"  # Zustand beibehalten
        }
    }

    return consumption_fig, feed_in_fig, net_usage_fig, combined_fig, f"Stromverbrauch: {total_consumption_kwh:.4f} kWh", f"Verschenkter Strom: {surplus_energy_kwh:.4f} kWh", f"Erzeugte Energie: {generated_energy_kwh:.4f} kWh"


# Anwendung starten
if __name__ == "__main__":
    load_data_log()  # Daten beim Start laden
    load_statistics_log()
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)
