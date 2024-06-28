from flask import Flask
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import requests
from dash.exceptions import PreventUpdate
import pandas as pd
import os

# Initialize Flask app
server = Flask(__name__)

# Initialize Dash app
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout of the dashboard
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Input(id="device-id-input", placeholder="Enter Device ID", type="text"),
            dbc.Button("Add Device ID", id="submit-button", color="primary", className="mr-2"),
            html.Div(id="error-message", style={"color": "red"}),
            dcc.Interval(id='interval-component', interval=5.1*1000, n_intervals=0, disabled=True)
        ], width=4),
    ]),
    dbc.Row([
        dbc.Col([
            html.Div(id='data-table')
        ])
    ])
], fluid=True)

# Global variable to hold the data
data_df = pd.DataFrame()

@app.callback(
    Output('interval-component', 'disabled'),
    Output('error-message', 'children'),
    Output('data-table', 'children'),
    Input('submit-button', 'n_clicks'),
    Input('interval-component', 'n_intervals'),
    State('device-id-input', 'value')
)
def update_output(n_clicks, n_intervals, device_id):
    global data_df

    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'submit-button':
        if not device_id:
            return True, "Please enter a device ID.", ""

        url = f"https://q17jj3lu0l.execute-api.ap-south-1.amazonaws.com/dev/data/realtime?deviceid={device_id}"
        response = requests.get(url)

        if response.text == "No data found for the given device ID":
            return True, "No data found for the given device ID", ""

        data = response.json()
        filtered_data = {k: v for k, v in data.items() if k not in ['ts', 'did', 'ttlf']}
        ordered_data = {'deviceid': filtered_data.pop('deviceid'), 'timestamp': filtered_data.pop('timestamp'), **filtered_data}
        data_df = pd.DataFrame([ordered_data])  # Reset DataFrame with new device ID data

        table = dbc.Table.from_dataframe(data_df, striped=True, bordered=True, hover=True)

        return False, "", table

    elif trigger_id == 'interval-component':
        if n_intervals == 0:
            raise PreventUpdate

        url = f"https://q17jj3lu0l.execute-api.ap-south-1.amazonaws.com/dev/data/realtime?deviceid={device_id}"
        response = requests.get(url)

        if response.text == "No data found for the given device ID":
            raise PreventUpdate

        data = response.json()
        filtered_data = {k: v for k, v in data.items() if k not in ['ts', 'did', 'ttlf']}
        ordered_data = {'deviceid': filtered_data.pop('deviceid'), 'timestamp': filtered_data.pop('timestamp'), **filtered_data}
        new_data_df = pd.DataFrame([ordered_data], columns=data_df.columns)
        data_df = pd.concat([data_df, new_data_df], ignore_index=True)

        table = dbc.Table.from_dataframe(data_df, striped=True, bordered=True, hover=True)

        return dash.no_update, dash.no_update, table

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)), debug=True)

