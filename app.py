from flask import Flask, session
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
import requests
from dash.exceptions import PreventUpdate
import pandas as pd
import os

# Initialize Flask app
server = Flask(__name__)
server.secret_key = os.urandom(24)

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
            html.Div([dbc.Button(f"Relay {i}", id=f"relay-button-{i}", color="secondary", className="mr-2", n_clicks=0) for i in range(12)], id='relay-buttons')
        ])
    ]),
    dbc.Row([
        dbc.Col([
            html.Div(id='data-table')
        ])
    ])
], fluid=True)

# Global variable to hold the data
data_df = pd.DataFrame()
relay_states = [0] * 12

@app.callback(
    Output('interval-component', 'disabled'),
    Output('error-message', 'children'),
    Output('data-table', 'children'),
    Output('relay-buttons', 'children'),
    Input('submit-button', 'n_clicks'),
    Input('interval-component', 'n_intervals'),
    [Input(f'relay-button-{i}', 'n_clicks') for i in range(12)],
    State('device-id-input', 'value')
)
def update_output(n_clicks, n_intervals, *args):
    global data_df, relay_states

    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'submit-button':
        if not args[-1]:
            return True, "Please enter a device ID.", "", []

        deviceid = args[-1]
        session['deviceid'] = deviceid
        url = f"https://q17jj3lu0l.execute-api.ap-south-1.amazonaws.com/dev/data/realtime?deviceid={deviceid}"
        response = requests.get(url)

        if response.text == "No data found for the given device ID":
            return True, "No data found for the given device ID", "", []

        data = response.json()
        filtered_data = {k: v for k, v in data.items() if k not in ['ts', 'did', 'ttlf']}
        ordered_data = {'deviceid': filtered_data.pop('deviceid'), 'timestamp': filtered_data.pop('timestamp'), **filtered_data}
        data_df = pd.DataFrame([ordered_data])  # Reset DataFrame with new device ID data

        # Update relay states
        rel_value = int(ordered_data.get('rel', 0))
        relay_states = [(rel_value >> i) & 1 for i in range(12)]

        table = dbc.Table.from_dataframe(data_df, striped=True, bordered=True, hover=True)

        relay_buttons = [dbc.Button(f"Relay {i}", id=f"relay-button-{i}", color="success" if relay_states[i] else "danger", className="mr-2") for i in range(12)]

        return False, "", table, relay_buttons

    elif trigger_id == 'interval-component':
        if n_intervals == 0:
            raise PreventUpdate

        deviceid = session.get('deviceid')
        url = f"https://q17jj3lu0l.execute-api.ap-south-1.amazonaws.com/dev/data/realtime?deviceid={deviceid}"
        response = requests.get(url)

        if response.text == "No data found for the given device ID":
            raise PreventUpdate

        data = response.json()
        filtered_data = {k: v for k, v in data.items() if k not in ['ts', 'did', 'ttlf']}
        ordered_data = {'deviceid': filtered_data.pop('deviceid'), 'timestamp': filtered_data.pop('timestamp'), **filtered_data}
        new_data_df = pd.DataFrame([ordered_data], columns=data_df.columns)
        data_df = pd.concat([data_df, new_data_df], ignore_index=True)

        # Update relay states
        rel_value = int(ordered_data.get('rel', 0))
        relay_states = [(rel_value >> i) & 1 for i in range(12)]

        table = dbc.Table.from_dataframe(data_df, striped=True, bordered=True, hover=True)

        relay_buttons = [dbc.Button(f"Relay {i}", id=f"relay-button-{i}", color="success" if relay_states[i] else "danger", className="mr-2") for i in range(12)]

        return dash.no_update, dash.no_update, table, relay_buttons

    else:
        relay_button_index = int(trigger_id.split('-')[-1])
        current_state = relay_states[relay_button_index]

        # Toggle relay state
        new_state = 1 - current_state
        relay_states[relay_button_index] = new_state

        deviceid = session.get('deviceid')
        url = f"https://q17jj3lu0l.execute-api.ap-south-1.amazonaws.com/dev/commands?deviceid={deviceid}"
        body = {f"relay{relay_button_index + 1}": new_state}
        requests.post(url, json=body)

        # Update button color
        relay_buttons = [dbc.Button(f"Relay {i}", id=f"relay-button-{i}", color="success" if relay_states[i] else "danger", className="mr-2") for i in range(12)]

        return dash.no_update, dash.no_update, dash.no_update, relay_buttons

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=int(os.environ.get('PORT', 8050)), debug=True)

