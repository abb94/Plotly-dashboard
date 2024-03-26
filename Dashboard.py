#!/usr/bin/env python
# coding: utf-8

# In[9]:


#Import libraries
import datetime
import yfinance as yf
import plotly.graph_objects as go
import dash
from dash import dash_table
import json
import requests
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State


# In[10]:


# List of Stock symbols from https://finance.yahoo.com/
shares = ["XRP-USD",
          "ETH-USD",
          "KNC-USD",
          "ETC-USD",
          "ZRX-USD",
          "XLM-USD",
          "SFM-USD",
          "DANSKE.CO",
          "AAL",
          "HTZ",
          "HTZWW",
          "SAAB-B.ST",
]
selections = ['Select all']
for stock in shares: 
    selections.append(stock)


# In[11]:


#Friendly name for shares. 
share_name = {"Select all" : "Select all",
              "XRP-USD" : "XRP",
              "ETH-USD" : "ETH",
              "KNC-USD" : "KNC",
              "ETC-USD" : "ETC",
              "ZRX-USD" : "ZRX",
              "XLM-USD" : "SAFE",
              "SFM-USD" : "XLM",
              "DANSKE.CO" : "Danske Bank",
              "AAL" : "American Airlines",
              "HTZ" : "Hertz ZZ",
              "HTZWW" : "Hertz WW",
              "SAAB-B.ST" : "SAAB",
}
    


# In[12]:


#Mapped currency of mapped shares. 
share_currency = {"XRP-USD" : "USD",
                  "ETH-USD" : "USD",
                  "KNC-USD" : "USD",
                  "ETC-USD" : "USD",
                  "ZRX-USD" : "USD",
                  "XLM-USD" : "USD",
                  "SFM-USD" : "USD",
                  "DANSKE.CO" : "DKK",
                  "AAL" : "USD",
                  "HTZ" : "EUR",
                  "HTZWW" : "EUR",
                  "SAAB-B.ST" : "SEK",
}
# Unique currencies
used_currencies = set(share_currency.values())


# In[13]:


#API key for 
api_key = "API_KEY_HERE"
base_currency = "DKK"

currencies_text = str()

#Append each unique currency to a string
for currency in used_currencies: 
    currencies_text = currencies_text + currency + ","
    
#Pass currency string to get exchange rate to base_currency
currency_rates = requests.get(
            f"https://api.currencybeacon.com/v1/latest/?base={base_currency}&symbols={currencies_text}&api_key={api_key}")

#Generate dictionary
currency_rate_dict = dict(currency_rates.json().get('response').get('rates'))

#Dict for mapping exchange rate. 
currency_multiplier = {}

#Map stocks currency with current exchange rate. 
for stock in share_currency: 
    currency_multiplier.update({stock : currency_rate_dict[share_currency[stock]]})


# In[14]:


#Strike price for each Stock symbol. 
price_shares =  {"XRP-USD" : 1.19,
                 "ETH-USD" : 855.92,
                 "KNC-USD" : 3.97,
                 "ETC-USD" : 34.06,
                 "ZRX-USD" : 2.34,
                 "XLM-USD" : 0.53,
                 "SFM-USD" : 0.00584,
                 "DANSKE.CO" : 76.72,
                 "AAL" : 86.36,
                 "HTZ" : 17.65,
                 "HTZWW" : 17.65,
                 "SAAB-B.ST" : 259.54,
}


# In[15]:


# No. of shares. 
no_shares = {"XRP-USD" : 1,
             "ETH-USD" : 1,
             "KNC-USD" : 1,
             "ETC-USD" : 1,
             "ZRX-USD" : 1,
             "XLM-USD" : 1,
             "SFM-USD" : 1,
             "DANSKE.CO" : 1,
             "AAL" : 2,
             "HTZ" : 1,
             "HTZWW" : 1,
             "SAAB-B.ST" : 1,
}


# In[16]:


#For each stock get 2 year data span of stock value. 
def fetch_data(): 
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=730)

    # Fetch the data for each ticker symbol
    data = yf.download(shares, start=start_date, end=end_date, progress = False)
    data = data["Close"]
    data = data.copy()
    data.fillna(0,inplace = True)
    data = (data / currency_multiplier)
    data = data.round(2)
    for date in data.index: 
        for k in shares:
            if data.loc[date][k] == 0:
                prev_date = date - datetime.timedelta(days = 1)
                try: 
                    data.loc[date][k] = data.loc[prev_date][k]
                except: 
                    pass
            else: 
                pass


    portfolio_value = (data * no_shares).sum(axis=1)
    portfolio_value = portfolio_value.round(2)
    for col in data: 
        data[col] = data[col].values*no_shares[col]
    return data, portfolio_value


# In[17]:


#Create dashboard on Stock data. 
app = dash.Dash(__name__)
data, portfolio_value = fetch_data()
app.layout = html.Div(
    children=[
        html.H1("Stock Value Dashboard", style={'text-align': 'center'}),
        html.Br(),
        html.H3(id="portfolio-value", style={'text-align' : 'left'}),
        html.Button("Update", id="update-dataset-button", n_clicks=-1),
        dcc.Graph(id="stock-value-graph"),
        dcc.Dropdown(
            id="stock-dropdown",
            options=[{"label": share_name[_option], "value": _option} for _option in selections],
            value=selections[0],
        ),
        html.H3("Latest price in DKK", style={'text-align': 'left'}),
        dash_table.DataTable(
            id='latest-data-table',
            columns=[{"name": share_name[col], "id": col} for col in data.columns],
            data=data.tail(1).to_dict('records'),
        ),
    ]
)



@app.callback(
    Output("stock-value-graph", "figure"),
    Output("portfolio-value", "children"),
    Output("latest-data-table", "data"),
    Input("stock-dropdown", "value"),
    Input("update-dataset-button", "n_clicks"),
    State("update-dataset-button", "n_clicks"),
)
def update_stock_value_graph(selected_stock, n_clicks, n_clicks_state):
    global data 
    global portfolio_value 
    ctx = dash.callback_context

    if not ctx.triggered:
        return dash.no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "stock-dropdown":
        
        updated_portfolio_value = f"Current Portfolio Value: {round((data.tail(1) * no_shares).sum(axis=1).values[0], 2)} DKK as of {data.tail(1).index[0].strftime('%d-%m-%Y')}"
        
        if selected_stock == "Select all":
            fig_overtime = go.Figure(data=go.Scatter(x=data.index, y=portfolio_value))
            fig_overtime.update_layout(
                title="Portfolio value over time",
                xaxis_title="Date",
                yaxis_title="Value",
                yaxis_tickprefix="DKK ",
                yaxis_tickformat=".2f",
                yaxis_showgrid=True,
                yaxis_gridcolor="lightgray"
        )
        else:
            fig_overtime = go.Figure(data=go.Scatter(x=data.index, y=data[selected_stock]))
            fig_overtime.update_layout(
                title=f"Value of {share_name[selected_stock]} over time",
                xaxis_title="Date",
                yaxis_title="Value",
                yaxis_tickprefix="DKK ",
                yaxis_tickformat=".2f",
                yaxis_showgrid=True,
                yaxis_gridcolor="lightgray"
        )
        
        
        updated_data_table = data.tail(1).to_dict('records')
        
        return fig_overtime, updated_portfolio_value, updated_data_table
    
    elif trigger_id == "update-dataset-button":
        data, portfolio_value = fetch_data()
        trigger_id
        if n_clicks != n_clicks_state:
            data, portfolio_value = fetch_data()
        
        
        updated_portfolio_value = f"Current Portfolio Value: {round((data.tail(1) * no_shares).sum(axis=1).values[0], 2)} DKK as of {data.tail(1).index[0].strftime('%d-%m-%Y')}"
        
        if selected_stock == "Select all":
            fig_overtime = go.Figure(data=go.Scatter(x=data.index, y=portfolio_value))
            fig_overtime.update_layout(
                title="Portfolio value over time",
                xaxis_title="Date",
                yaxis_title="Value",
                yaxis_tickprefix="DKK ",
                yaxis_tickformat=".2f",
                yaxis_showgrid=True,
                yaxis_gridcolor="lightgray"
        )
        else:
            fig_overtime = go.Figure(data=go.Scatter(x=data.index, y=data[selected_stock]))
            fig_overtime.update_layout(
                title=f"Value of {share_name[selected_stock]} over time",
                xaxis_title="Date",
                yaxis_title="Value",
                yaxis_tickprefix="DKK ",
                yaxis_tickformat=".2f",
                yaxis_showgrid=True,
                yaxis_gridcolor="lightgray"
        )
            
        updated_data_table = data.tail(1).to_dict('records')
        
        return fig_overtime, updated_portfolio_value, updated_data_table

    return dash.no_update

#Connect in browser at localhost - Press update button first time opening/running script. 
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=9000)