import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
from dash import dash_table
from datetime import datetime, timedelta, date

# Global veri cache
DATA_CACHE = pd.DataFrame()

# Veri cekme fonksiyonu
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

# Ilk veri yuklemesi
DATA_CACHE = get_data()
custom_colors = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854"]

# Dash app baslangici
app = Dash(__name__)

# Layout
app.layout = html.Div([
    html.H2("Sloth NFT Market Performance Overview", style={"textAlign": "center", "marginBottom": "10px", "marginTop": "10px"}),

    dcc.DatePickerRange(
        id='date-picker',
        min_date_allowed=date(2023, 1, 1),
        max_date_allowed=date.today(),
        start_date=date.today() - timedelta(days=7),
        end_date=date.today(),
        style={"display": "block", "margin": "0 auto 10px auto","textAlign": "center"}
    ),

    html.Div([
        dcc.Graph(id='kpi-total-txn', style={"width": "32%", "display": "inline-block", "margin": "0 0.5%"}),
        dcc.Graph(id='kpi-offer-txn', style={"width": "32%", "display": "inline-block", "margin": "0 0.5%"}),
        dcc.Graph(id='kpi-total-volume', style={"width": "32%", "display": "inline-block", "margin": "0 0.5%"})
    ], style={"textAlign": "center", "marginBottom": "10px"}),
    
    html.Div([
        dcc.Graph(id="Pareto-plot", style={"width": "70%", "height": "600px"}),
        html.Div(id="image-box", style={"width": "30%", "padding": "20px", "borderLeft": "1px solid lightgray"})
    ], style={"display": "flex", "marginBottom": "10px"}),
    

    html.Div([
        dcc.Graph(id="scatter-plot", style={"width": "70%", "height": "600px"}),
        html.Div(id="image-box", style={"width": "30%", "padding": "20px", "borderLeft": "1px solid lightgray"})
    ], style={"display": "flex", "marginBottom": "10px"}),

    html.Div([
        html.H4("Date Range Data", style={"marginTop": "10px"}),
        dash_table.DataTable(
            id='sales-table-html',
            columns=[
                {"name": "NFT", "id": "url", "presentation": "markdown"},
                {"name": "Date", "id": "date"},
                {"name": "Token", "id": "tokenId"},
                {"name": "Type", "id": "saleType"},
                {"name": "Price (USD)", "id": "priceUsd"},
            ],
            page_size=10,
            style_cell={"textAlign": "left"},
            style_data_conditional=[],
            style_data={"whiteSpace": "normal", "height": "auto"},
            markdown_options={"html": True},
        )
    ]),

    dcc.Interval(id='interval-component', interval=3600 * 1000, n_intervals=0)
], style={"fontFamily": "Arial, sans-serif", "padding": "10px"})


# KPI Guncelleme
@app.callback(
    Output('kpi-total-txn', 'figure'),
    Output('kpi-offer-txn', 'figure'),
    Output('kpi-total-volume', 'figure'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def update_kpis(start_date, end_date):
    df = filter_data_by_date(DATA_CACHE.copy(), start_date, end_date)
    total_txn = len(df)
    offer_txn = df[df['saleType'].isin(['COLLECTION_OFFER', 'OFFER'])].shape[0]
    total_volume = df['priceUsd'].sum()

    def gauge(title, value, max_value):
        return go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            gauge={'axis': {'range': [0, max_value]}, 'bar': {'color': "#2196f3"}},
            title={'text': title}
        ))

    return (
        gauge("Total Transactions", total_txn, max(100, total_txn * 1.2)),
        gauge("Offers Transactions", offer_txn, max(50, offer_txn * 1.2)),
        gauge("Total Volume", total_volume, max(1000, total_volume * 1.2))
    )


# Scatter  plot
@app.callback(
    Output("scatter-plot", "figure"),
    Input("interval-component", "n_intervals"),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def create_scatter(_, start_date, end_date):
    df = filter_data_by_date(DATA_CACHE.copy(), start_date, end_date)
    sale_types = df['saleType'].unique()
    color_map = {s: custom_colors[i % len(custom_colors)] for i, s in enumerate(sale_types)}
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

# Pareto plot
@app.callback(
    Output("Pareto-plot", "figure"),
    Input("interval-component", "n_intervals"),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def create_pareto(_, start_date, end_date):
    df = filter_data_by_date(DATA_CACHE.copy(), start_date, end_date)

    # Günlük satış adedi türlerine göre
    daily_count_by_type = (
        df.groupby([df["date"].dt.date, "saleType"])["priceUsd"]
          .count()
          .unstack(fill_value=0)
          .sort_index()
    )

    # Kümülatif satış tutarı (USD)
    cumsum_sales = (
        df.groupby(df["date"].dt.date)["priceUsd"]
          .sum()
          .sort_index()
          .cumsum()
    )

    # Grafik
    fig = go.Figure()

    # Stacked bar (satış adetleri)
    for col in daily_count_by_type.columns:
        fig.add_trace(go.Bar(
            x=daily_count_by_type.index,
            y=daily_count_by_type[col],
            name=col
        ))

    # Pareto çizgisi (kümülatif USD)
    fig.add_trace(go.Scatter(
        x=cumsum_sales.index,
        y=cumsum_sales.values,
        mode="lines+markers+text",
        text=[f"{v/1000:.1f}K" if v >= 1000 else str(int(v)) for v in cumsum_sales],
        textposition="top center",
        name="Cumulative Sales (USD)",
        line=dict(color="red", width=2)
    ))

    # Layout ayarları
    fig.update_layout(
        barmode="stack",
        title="Daily Sales Count by Type with Cumulative Sales",
        xaxis_title="Date",
        yaxis_title="Number of Sales",
        yaxis=dict(tickmode="linear", dtick=1),  # tam sayılar
        legend=dict(title="Sale Type", x=1.02, y=1, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    return fig





# Tablo
@app.callback(
    Output("sales-table-html", "data"),
    Input("interval-component", "n_intervals"),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def update_table(_, start_date, end_date):
    global DATA_CACHE
    DATA_CACHE = get_data()
    df = filter_data_by_date(DATA_CACHE.copy(), start_date, end_date)
    df = df.sort_values(by='date', ascending=False)
    df['url'] = df['url'].apply(lambda x: f"<div style='text-align:center'><img src='{x}' style='height:45px;width:45px;'></div>")
    df['date'] = df['date'].dt.date
    df['priceUsd'] = df['priceUsd'].apply(lambda x: f"${x:,.2f}")
    return df[['url', 'date', 'tokenId', 'saleType', 'priceUsd']].to_dict('records')


# Hover Resmi
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


# filter 
def filter_data_by_date(df, start_date, end_date):
    if start_date and end_date:
        start = pd.to_datetime(start_date).date()
        end = pd.to_datetime(end_date).date()
        df['date_only'] = df['date'].dt.date
        df = df[(df['date_only'] >= start) & (df['date_only'] <= end)]
    return df

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8080)
