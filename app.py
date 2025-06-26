import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go

url = "https://docs.google.com/spreadsheets/d/1Ou6kgRx5VuhopKeBwztKs1Aps-KIxNz4YCEcOUbmDrc/export?format=csv"
df = pd.read_csv(url)
df['date'] = pd.to_datetime(df['date'])

custom_colors = ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854"]
sale_types = df['saleType'].unique()
color_map = {sale_type: custom_colors[i % len(custom_colors)] for i, sale_type in enumerate(sale_types)}

app = Dash(__name__)
server = app.server  # ⬅️ Render için şart

app.layout = html.Div([
    html.Div([
        dcc.Graph(id="scatter-plot", style={"width": "70%", "height": "600px"}),
        html.Div(id="image-box", style={
            "width": "30%", "padding": "20px", "borderLeft": "1px solid lightgray"
        })
    ], style={"display": "flex"})
])

@app.callback(
    Output("scatter-plot", "figure"),
    Input("scatter-plot", "id")
)
def create_figure(_):
    fig = go.Figure()
    for sale_type in sale_types:
        filtered = df[df['saleType'] == sale_type]
        fig.add_trace(go.Scatter(
            x=filtered['date'],
            y=filtered['priceUsd'],
            mode='markers',
            name=sale_type,
            marker=dict(size=10, color=color_map[sale_type]),
            customdata=filtered[['tokenId', 'priceUsd', 'saleType', 'url','date']],
            hovertemplate="<b>Token:</b> %{customdata[0]}<br>Price: $%{customdata[1]}<br>Type: %{customdata[2]}<extra></extra>"
        ))

    fig.update_layout(
        title="NFT Satışları",
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
    return html.Div("Bir NFT'nin üzerine gelin...", style={"color": "gray", "fontSize": 16})

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8080)
