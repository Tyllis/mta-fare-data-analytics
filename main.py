# -*- coding: utf-8 -*-
"""
@author: junyan
"""

import os, gc, dash, dash_table
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, MATCH, ALL
from datetime import timedelta, datetime
from kaggle.api.kaggle_api_extended import KaggleApi

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title='MTA Subway Fare Data Visualization'
)
server = app.server

data_url = os.environ['DATA_URL']
api = KaggleApi()
api.authenticate()
api.dataset_download_file(data_url, file_name='main.csv')
api.dataset_download_file(data_url, file_name='forecast.csv')

df = pd.read_csv('./main.csv.zip')
geo_df = pd.read_csv('./station_gis.csv')
try:
    forecast_df = pd.read_csv('./forecast.csv.zip')
except:
    forecast_df = pd.read_csv('./forecast.csv')
start_date = '2020-01-04'

df.WEEK = df.WEEK.apply(lambda x: datetime.strptime(x, '%Y-%m-%d'))
df.drop(columns=['1-D UNL', '14-D UNL', '14-D RFM UNL'], inplace=True)
card_types = df.drop(columns=['WEEK', 'REMOTE', 'STATION']).sum(axis=0).sort_values(ascending=False).index.tolist()
stations = geo_df['STATION'].sort_values().unique().tolist()
week_ending_cur = df.WEEK.max()
week_ending_old = week_ending_cur - timedelta(weeks=(week_ending_cur.year - 2019) * 52)

df_sel = df[df['STATION'].isin(stations)].copy()
df_sel['row_sum'] = df_sel[card_types].sum(axis=1)
df_cur = df_sel[df_sel['WEEK'] == week_ending_cur][['STATION', 'row_sum']].groupby('STATION', as_index=False).sum()
df_old = df_sel[df_sel['WEEK'] == week_ending_old][['STATION', 'row_sum']].groupby('STATION', as_index=False).sum()
df_meg = df_cur.merge(df_old, how='left', on='STATION')
df_meg['ratio'] = round(df_meg.row_sum_x / df_meg.row_sum_y, 4)
df_meg['Recent Daily'] = (df_meg['row_sum_x'] / 7).apply(lambda x: '{:,}'.format(int(x) if x == x else 0))
df_meg['Pre-pandemic Daily'] = (df_meg['row_sum_y'] / 7).apply(lambda x: '{:,}'.format(int(x) if x == x else 0))
df_meg = df_meg.merge(geo_df, how='left', on='STATION')
df_meg['size'] = df_meg['row_sum_x'].fillna(0) / 7
df_meg['ratio'] = df_meg['ratio'].fillna(0)
df = df[df.WEEK >= datetime.strptime(start_date, '%Y-%m-%d')]

del df_sel, df_cur, df_old
_ = gc.collect()

fig = px.scatter_mapbox(
    df_meg, lat="lat", lon="lon", size='size', color='ratio', zoom=10,
    labels={'ratio': '% Recovery'},
    custom_data=['STATION', 'Pre-pandemic Daily', 'Recent Daily', 'ratio'],
    range_color=[0, df_meg['ratio'].quantile(0.75)],
    color_continuous_scale=px.colors.sequential.Blues
)
fig.update_layout(
    mapbox_style="carto-positron",
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    coloraxis={'colorbar': {'len': 0.5, 'x': 0, 'tickformat': '.0%', 'yanchor': 'top'}}
)
fig.update_traces(
    hovertemplate=
    '<b>Station: %{customdata[0]}</b> <br>' +
    'Recent Average Daily: %{customdata[2]} <br>' +
    'Pre-pandemic Daily: %{customdata[1]} <br>' +
    '% Recovery : %{customdata[3]:.2%}'
)

card_class = 'card border-info'
css_style = {'margin-top': '35px', 'margin-bottom': '75px',
             'margin-left': '75px', 'margin-right': '75px'}

card_intro_text = dbc.Card([
    dbc.CardBody([
        html.H5('Welcome to the MTA Subway Fare Data Analytics Dashboard',
                style={'font-weight': 'bold'}),
        html.P([
            'Last updated: ' + datetime.strftime(week_ending_cur, '%b %d, %Y'),
            html.Br(),
            'Data source: ',
            html.A('http://web.mta.info/developers/fare.html',
                   href='http://web.mta.info/developers/fare.html'),
            html.Br(),
            'GitHub repository: ',
            html.A('https://github.com/Tyllis/mta-fare-data-analytics',
                   href='https://github.com/Tyllis/mta-fare-data-analytics')
        ]),
        html.P([
            'The New York City Transit subway fare data are based on the number of MetroCard ' +
            'swipes made each week by customers entering each station of the New York City ' +
            'Subway, PATH, AirTrain JFK and the Roosevelt Island Tram. The data is released ' +
            'one week after the recorded week. This dashboard is updated every Monday after the ' +
            'new data is released.'
        ]),
        html.P([
            'On the Pandemic Recovery map, the size of the circle shows the relative ' +
            'volume of MetroCard swipes at each station for the recent week ' +
            '(larger means more swipes); the color reflects the percent recovery, ' +
            'calculated by dividing the recent volume by the pre-pandemic ' +
            'volume. The pre-pandemic data is defined as the 2019 data at the week ' +
            'corresponding to recent week. '
        ]),
        html.P([
            'Explore the map by using the "Box Select" or "Lasso Select" to select ' +
            'the stations of interest. The Trend, Forecast, Ranking, and Table will interact ' +
            'based on the stations selected. Clicking on the buttons in the Selected ' +
            'Stations area toggles the stations on/off. To reset to default selection ' +
            '(all stations), double click on any area on the map.'
        ]),
        html.P([
            'For the trend graph, double click on one of the MetroCard type in the legend to ' +
            'select the card type of interest; then single click to add additional cards. ' +
            'Double click again on the legend to reset selection. ' +
            'The MetroCard type description can be found ',
            html.A('here',
                   href='http://web.mta.info/developers/resources/nyct/fares/fare_type_description.txt'),
            '. Explore the ranking graph by dragging the slider to view station ranking ' +
            'in different time period, or use the play button for an animation through time. Ridership forecast ' +
            'is done using AutoARIMA. For detail see ',
            html.A('here',
                   href='https://github.com/nixtla/statsforecast'),
            '.'
        ])
    ])
],
    className=card_class
)

card_selected_stations = dbc.Card([
    dbc.FormGroup([
        dbc.CardHeader('Selected Stations:',
                       style={'font-weight': 'bold'}
                       ),
        html.Div(
            id='station_button_group',
            style={"maxHeight": "500px", "overflow": "scroll", 'align': 'center'}
        )
    ])
],
    className=card_class
)

card_mapbox = dbc.Card([
    dbc.CardHeader("NYC Subway Stations Pandemic Recovery Map",
                   style={'font-weight': 'bold'}
                   ),
    dbc.CardBody(
        dcc.Graph(
            id='mapbox_scatter',
            figure=fig
        )
    )
],
    className=card_class
)

card_barplot = dbc.Card([
    dbc.CardHeader("Stations Ranked by Total MetroCard Swipes",
                   style={'font-weight': 'bold'}
                   ),
    dbc.CardBody(
        dcc.Graph(
            id='bar_plot'
        )
    )
],
    className=card_class
)

card_areaplot = dbc.Card([
    dbc.CardHeader("Trend for Selected Stations",
                   style={'font-weight': 'bold'}
                   ),
    dbc.CardBody(
        dcc.Graph(
            id='area_plot'
        )
    )
],
    className=card_class
)

card_forecastplot = dbc.Card([
    dbc.CardHeader("Forecast for Selected Stations",
                   style={'font-weight': 'bold'}
                   ),
    dbc.CardBody(
        dcc.Graph(
            id='forecast_plot'
        )
    )
],
    className=card_class
)

card_datatable = dbc.Card([
    dbc.CardHeader("Data Table for Selected Stations",
                   style={'font-weight': 'bold'}
                   ),
    dbc.CardBody(
        dash_table.DataTable(
            id='table',

            columns=[{'id': c, 'name': c} for c in ['Station', 'Recent Daily',
                                                    'Pre-pandemic Daily',
                                                    'Recovery Ratio', 'lat', 'lon']],
            page_action='none',
            fixed_rows={'headers': True},
            style_table={'height': '500px', 'overflowY': 'auto', 'overflowX': 'auto'},
            style_cell={'minWidth': 100, 'maxWidth': 120}
        )
    )
],
    className=card_class
)

app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            dbc.Row(dbc.Col(card_intro_text)),
        ],
            md=4
        ),
        dbc.Col([
            dbc.Row(
                dbc.Col(
                    dbc.Tabs([
                        dbc.Tab(card_mapbox, label='Map'),
                        dbc.Tab(card_areaplot, label='Trend'),
                        dbc.Tab(card_forecastplot, label='Forecast'),
                        dbc.Tab(card_barplot, label='Ranking'),
                        dbc.Tab(card_datatable, label='Table')
                    ])
                )
            ),
            html.Br(),
            dbc.Row(dbc.Col(card_selected_stations))
        ],
            md=8
        )
    ]),

    dcc.Store(id='selected_station'),
    dcc.Store(id='button_filtered')
],
    style=css_style
)


@app.callback(
    Output('station_button_group', 'children'),
    Output('selected_station', 'data'),
    Input('mapbox_scatter', 'selectedData')
)
def create_buttons(mapbox_selected):
    if mapbox_selected is None:
        mapbox_selected = {'points': []}
    if len(mapbox_selected['points']) == 0:
        selected_station = stations
    else:
        selected_station = [mapbox_selected['points'][i]['customdata'][0]
                            for i in range(len(mapbox_selected['points']))]
    selected_station.sort()
    button_list = []
    if set(selected_station) == set(stations):
        selected_station = ['ALL STATIONS']
        button = dbc.Button('ALL STATIONS', outline=True, color="success", size='sm',
                            className="mr-1", n_clicks=0, id={'type': 'station_button', 'index': 'ALL STATIONS'})
        button_list.append(button)
    else:
        for station in selected_station:
            button = dbc.Button(station, outline=True, color="success", size='sm',
                                className="mr-1", n_clicks=0, id={'type': 'station_button', 'index': station})
            button_list.append(button)
    return button_list, selected_station


@app.callback(
    Output({'type': 'station_button', 'index': MATCH}, 'color'),
    Input({'type': 'station_button', 'index': MATCH}, 'n_clicks'),
    prevent_initial_call=True
)
def button_color_change(clicks):
    if clicks % 2 == 0:
        color = 'success'
    else:
        color = 'danger'
    return color


@app.callback(
    Output('button_filtered', 'data'),
    Input('selected_station', 'data'),
    Input({'type': 'station_button', 'index': ALL}, 'n_clicks')
)
def button_filter(selected_station, clicks):
    even_clicks_idx = [idx for idx, val in enumerate(clicks) if val % 2 == 0]
    filtered_station = [selected_station[idx] for idx in even_clicks_idx]
    if 'ALL STATIONS' in filtered_station:
        filtered_station = stations
    return filtered_station


@app.callback(
    Output('bar_plot', 'figure'),
    Input('button_filtered', 'data')
)
def create_barplot(selected_station):
    if len(selected_station) == 0:
        return go.Figure(data=[go.Scatter(x=[], y=[])])
    num_bars = 15
    cols = ['WEEK', 'REMOTE', 'STATION'] + card_types
    tmp = df[df['STATION'].isin(selected_station)][cols].copy()
    tmp = tmp.groupby(['WEEK', 'STATION'], as_index=False).sum()
    tmp = pd.melt(tmp, id_vars=['WEEK', 'STATION'], value_vars=card_types, var_name='card_type', value_name='swipes')
    tmp = tmp.groupby(['WEEK', 'STATION'], as_index=False).sum()
    tmp_ = tmp.groupby('WEEK')['swipes'].nlargest(num_bars)
    try:
        time, indx = zip(*tmp_.index.tolist())
    except:
        indx = tmp_.index.tolist()
    tmp = tmp.iloc[list(indx)]
    tmp.WEEK = tmp.WEEK.apply(lambda x: '{:%Y-%m-%d}'.format(x))
    tmp = tmp.reset_index(drop=True)
    tmp['swipes'] = (tmp['swipes'] / 7).astype('int')
    max_range = tmp.groupby(['WEEK', 'STATION'], as_index=False)['swipes'].sum()['swipes'].max()

    fig = px.bar(
        tmp, y='STATION', x='swipes', animation_frame='WEEK',
        range_x=[0, max_range], orientation='h', template='seaborn',
        labels={'STATION': 'Station Name',
                'WEEK': 'Week Ending',
                'swipes': 'Average Daily MetroCard Swipes'},
        custom_data=['STATION', 'WEEK', 'swipes']
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"))

    fig.update_traces(
        hovertemplate=
        'Station: %{customdata[0]} <br>' +
        'Week Ending: %{customdata[1]} <br>' +
        'Swipes: %{customdata[2]:,}<extra></extra>'
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    return fig


@app.callback(
    Output('area_plot', 'figure'),
    Input('button_filtered', 'data')
)
def create_areaplot(selected_station):
    if len(selected_station) == 0:
        return go.Figure(data=[go.Scatter(x=[], y=[])])
    cols = ['WEEK', 'REMOTE', 'STATION'] + card_types
    tmp = df[df['STATION'].isin(selected_station)][cols].copy()
    tmp = tmp.groupby('WEEK', as_index=False).sum()
    tmp = pd.melt(tmp, id_vars=['WEEK'], value_vars=card_types, var_name='card_type', value_name='swipes')
    tmp.WEEK = tmp.WEEK.apply(lambda x: '{:%Y-%m-%d}'.format(x))
    sorted_cards = tmp.groupby('card_type', as_index=False).mean(). \
        sort_values('swipes', ascending=False).card_type.tolist()
    tmp = tmp.set_index('card_type').loc[sorted_cards]
    tmp = tmp.reset_index()
    tmp['swipes'] = (tmp['swipes'] / 7).astype('int')
    fig = px.area(
        tmp, x='WEEK', y='swipes', color='card_type', template='seaborn',
        labels={'card_type': 'MetroCard Type',
                'WEEK': 'Date',
                'swipes': 'Average Daily MetroCard Swipes'},
        custom_data=['card_type', 'swipes', 'WEEK']
    )
    fig.update_xaxes(spikemode='across', spikethickness=1)
    fig.update_traces(
        hovertemplate=
        '<b>MetroCard Type: %{customdata[0]}</b> <br>' +
        'MetroCard Swipes: %{customdata[1]:,} <br>' +
        'Week Ending: %{customdata[2]}<extra></extra>'
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    return fig


@app.callback(
    Output('forecast_plot', 'figure'),
    Input('button_filtered', 'data')
)
def create_forecastplot(selected_station):
    if len(selected_station) == 0:
        return go.Figure(data=[go.Scatter(x=[], y=[])])
    cols = ['WEEK', 'AutoARIMA', 'interval-95-square']
    tmp = forecast_df[forecast_df['STATION'].isin(selected_station)][cols].copy()
    tmp.WEEK = pd.to_datetime(tmp.WEEK)
    tmp = tmp.sort_values('WEEK').groupby('WEEK', as_index=False).sum()
    tmp['interval-95'] = tmp['interval-95-square'] ** 0.5
    tmp['lo-95'] = (tmp['AutoARIMA'] - tmp['interval-95']).astype('int')
    tmp['hi-95'] = (tmp['AutoARIMA'] + tmp['interval-95']).astype('int')
    tmp['Forecast'] = tmp['AutoARIMA'].astype('int')

    fig = go.Figure([
        go.Scatter(
            name='Forecast',
            x=tmp['WEEK'],
            y=tmp['Forecast'],
            line=dict(color='rgb(31, 119, 180)'),
            mode='lines',
            showlegend=False
        ),
        go.Scatter(
            name='95% Upper Bound',
            x=tmp['WEEK'],
            y=tmp['hi-95'],
            mode='lines',
            marker=dict(color="#444"),
            line=dict(width=0),
            showlegend=False
        ),
        go.Scatter(
            name='95% Lower Bound',
            x=tmp['WEEK'],
            y=tmp['lo-95'],
            marker=dict(color="#444"),
            line=dict(width=0),
            mode='lines',
            fillcolor='rgba(68, 68, 68, 0.3)',
            fill='tonexty',
            showlegend=False
        )
    ])

    fig.update_layout(
        yaxis_title='Forecast Daily MetroCard Swipes',
        xaxis_title='Date',
        hovermode="x",
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel_namelength=-1
    )

    return fig


@app.callback(
    Output('table', 'data'),
    Input('button_filtered', 'data')
)
def create_table(selected_station):
    selected_df = df_meg[df_meg.STATION.isin(selected_station)].copy()
    selected_df = selected_df[['STATION', 'Recent Daily', 'Pre-pandemic Daily', 'ratio', 'lat', 'lon', 'wiki']]
    selected_df = selected_df.rename(
        columns={'STATION': 'Station', 'ratio': 'Recovery Ratio', 'wiki': 'Wikipedia Link'})
    selected_df.lat = selected_df.lat.round(decimals=5)
    selected_df.lon = selected_df.lon.round(decimals=5)
    selected_df = selected_df.to_dict(orient='records')
    return selected_df


if __name__ == '__main__':
    app.run_server(debug=False, host="0.0.0.0", port=8080)