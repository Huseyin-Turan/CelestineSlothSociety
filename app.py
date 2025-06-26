## Son hali 

import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

# Global veri önbelleği
DATA_CACHE = pd.DataFrame()

def get_data():
    url = "https://docs.google.com/spreadsheets/d/1Ou6kgRx5VuhopKeBwztKs1Aps-KIxNz4YCEcOUbmDrc/export?format=csv"
    df = pd.read_csv(url)
    df['date'] = pd.to_datetime(df['date'])
    df['priceUsd'] = (
        df['priceUsd']
        .astype(str)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
        .astype(float))
    return df

# Başlangıçta veriyi çek
DATA_CACHE = get_data()


custom_colors = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854"]

app = Dash(__name__)

app.layout = html.Div([
    html.H2("NFT Satış Dashboard", style={"textAlign": "center", "marginBottom": "10px"}),

    html.Div([
        dcc.DatePickerRange(
            id='date-picker',
            min_date_allowed=date(2023, 1, 1),
            max_date_allowed=date.today(),
            start_date=date.today() - pd.Timedelta(days=7),
            end_date=date.today()
        )
    ], style={"textAlign": "center", "marginBottom": "30px"}),

    html.Div([
        dcc.Graph(id='kpi-total-txn', style={"width": "32%", "display": "inline-block", "margin": "0 0.5%"}),
        dcc.Graph(id='kpi-offer-txn', style={"width": "32%", "display": "inline-block", "margin": "0 0.5%"}),
        dcc.Graph(id='kpi-total-volume', style={"width": "32%", "display": "inline-block", "margin": "0 0.5%"})
    ], style={"textAlign": "center", "marginBottom": "30px"}),

    html.Div([
        dcc.Graph(id="scatter-plot", style={"width": "70%", "height": "600px"}),
        html.Div(id="image-box", style={
            "width": "30%", "padding": "20px", "borderLeft": "1px solid lightgray"
        })
    ], style={"display": "flex"}),

    html.Div([
        html.H4("Son 7 Günlük Satışlar", style={"marginTop": "40px"}),
        html.Table([
            html.Thead([
                html.Tr([
                    html.Th("NFT"),
                    html.Th("Date"),
                    html.Th("Token"),
                    html.Th("Type"),
                    html.Th("Price (USD)")
                ])
            ]),
            html.Tbody(id="sales-table-html")
        ], style={"width": "100%", "borderCollapse": "collapse", "marginTop": "20px"})
    ]),

    dcc.Interval(
        id='interval-component',
        interval=3600 * 1000,  # 1 saat
        n_intervals=0
    )
], style={"fontFamily": "Arial, sans-serif", "padding": "20px"})


@app.callback(
    Output('kpi-total-txn', 'figure'),
    Output('kpi-offer-txn', 'figure'),
    Output('kpi-total-volume', 'figure'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def update_dashboard(start_date, end_date):
    df = DATA_CACHE.copy()
    if start_date and end_date:
        start_date_obj = pd.to_datetime(start_date).date()
        end_date_obj = pd.to_datetime(end_date).date()
        df['date_only'] = df['date'].dt.date
        df = df[(df['date_only'] >= start_date_obj) & (df['date_only'] <= end_date_obj)]

    total_txn = len(df)
    offer_txn = df[df['saleType'].isin(['COLLECTION_OFFER', 'OFFER'])].shape[0]
    total_volume = df['priceUsd'].sum()

    def create_gauge(title, value, max_value, color):
        return go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            gauge={'axis': {'range': [0, max_value]}, 'bar': {'color': color}},
            title={'text': title}
        ))

    return (
        create_gauge("Total TXN", total_txn, max(100, total_txn * 1.2), "#2196f3"),
        create_gauge("Offer TXN", offer_txn, max(50, offer_txn * 1.2), "#2196f3"),
        create_gauge("Total Volume", total_volume, max(1000, total_volume * 1.2), "#2196f3")
    )


@app.callback(
    Output("sales-table-html", "children"),
    Input("interval-component", "n_intervals"),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def update_table(n_intervals,start_date,end_date):
    global DATA_CACHE
    DATA_CACHE = get_data()  # yenile
    df = DATA_CACHE.copy()

    if start_date and end_date:
        start_date_obj = pd.to_datetime(start_date).date()
        end_date_obj = pd.to_datetime(end_date).date()
        df['date_only'] = df['date'].dt.date
        df_recent = df[(df['date_only'] >= start_date_obj) & (df['date_only'] <= end_date_obj)]
    

    rows = []
    for _, row in df_recent.iterrows():
        rows.append(html.Tr([
            html.Td(html.Img(src=row['url'], style={"height": "40px", "width": "40px"})),
            html.Td(str(row['date'].date())),
            html.Td(row['tokenId']),
            html.Td(row['saleType']),
            html.Td(f"${row['priceUsd']:,.2f}")
        ]))
    return rows


@app.callback(
    Output("scatter-plot", "figure"),
    Input("interval-component", "n_intervals"),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def create_figure(n_intervals,start_date,end_date):
    df = DATA_CACHE.copy()
    if start_date and end_date:
        start_date_obj = pd.to_datetime(start_date).date()
        end_date_obj = pd.to_datetime(end_date).date()
        df['date_only'] = df['date'].dt.date
        df = df[(df['date_only'] >= start_date_obj) & (df['date_only'] <= end_date_obj)]
    sale_types = df['saleType'].unique()
    color_map = {sale_type: custom_colors[i % len(custom_colors)] for i, sale_type in enumerate(sale_types)}

    fig = go.Figure()
    for sale_type in sale_types:
        filtered = df[df['saleType'] == sale_type]
        fig.add_trace(go.Scatter(
            x=filtered['date'],
            y=filtered['priceUsd'],
            mode='markers',
            name=sale_type,
            marker=dict(size=10, color=color_map[sale_type]),
            customdata=filtered[['tokenId', 'priceUsd', 'saleType', 'url', 'date']],
            hovertemplate="<b>Token:</b> %{customdata[0]}<br>Price: $%{customdata[1]}<br>Type: %{customdata[2]}<extra></extra>"
        ))

    fig.update_layout(
        title="Daily Sales and Activity of Sloths",
        hovermode="closest",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    return fig


@app.callback(
    Output("image-box", "children"),
    Input("scatter-plot", "hoverData")
)
def show_image(hoverData):
    if hoverData:
        point = hoverData['points'][0]
        token_id, price, sale_type, url, date = point['customdata']
        return html.Div([
            html.Img(src=url, style={"width": "100%", "border": "1px solid #ddd", "borderRadius": "8px"}),
            html.H4(f"Token ID: {token_id}"),
            html.P(f"Date: {date}"),
            html.P(f"Type: {sale_type}"),
            html.P(f"Price: ${price}")
        ])
    return html.Div("...", style={"color": "gray", "fontSize": 16})

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8080)
