import os
import django
import sys
import numpy as np
from scipy.stats import linregress
from django.db.models import Sum
from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px
import pandas as pd
from django.db import DatabaseError

sys.path.append("C:\\Dev\\PSR_Data_Dev\\PSR_Dev")

# Set the Django settings module

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PSR_Dev.settings")
    django.setup()
except Exception as e:
    print(f"Falha ao configurar o Django: {e}")
    sys.exit(1)

# 3. Importar modelos
from myapp.models import Notifications, Regions

def get_notification_data():
    """Buscar dados de notificação do banco de dados"""
    try:
        data = Notifications.objects.all().values(
            'notification_id', 'disease__disease_name', 'region',
            'notification_week', 'notification_year',
            'cases_confirmed'
        )
        return pd.DataFrame(data)
    except DatabaseError as e:
        print(f"Erro no banco de dados: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return None

def process_data(df_data):
    """Processar o DataFrame para obter somas semanais"""
    if df_data is None or df_data.empty:
        return None
    
    # Agrupar por doença, ano e semana e somar os casos confirmados
    sum_case_week = df_data.groupby(
        ['disease__disease_name', 'notification_year', 'notification_week']
    )['cases_confirmed'].sum().reset_index()
    
    # Renomear colunas
    sum_case_week.rename(columns={
        'disease__disease_name': 'Disease',
        'notification_year': 'Year',
        'notification_week': 'Week',
        'cases_confirmed': 'Cases'
    }, inplace=True)
    
    return sum_case_week

def calculate_apc_for_window(cases):
    """Calcular APC usando regressão linear para uma janela de pontos"""
    apcs = []
    slopes = []
    
    # Para cada par de pontos consecutivos
    for i in range(1, len(cases)):
        if cases[i-1] > 0 and cases[i] > 0:  # Evitar log de números negativos ou zero
            x = np.array([0, 1])
            y = np.log(np.array([cases[i-1], cases[i]]))  
            slope, intercept, r_value, p_value, std_err = linregress(x, y)
            apc = (np.exp(slope) - 1) * 100
        else:
            apc = 0
            slope = 0
            
        apcs.append(apc)
        slopes.append(slope)
    
    apcs.insert(0, 0)
    slopes.insert(0, 0)
    
    return apcs, slopes

def create_dash_app(df):
    """Criar e configurar a aplicação Dash"""
    app = Dash(__name__)

    # Obter lista única de doenças
    unique_diseases = df['Disease'].unique()

    # Layout da aplicação
    app.layout = html.Div([
        html.H1("Disease Cases Dashboard", style={'textAlign': 'center'}),

        # Dropdown para selecionar a doença
        html.Div([
            html.Label("Select Disease:", style={'font-weight': 'bold'}),
            dcc.Dropdown(
                id="disease-dropdown",
                options=[{"label": d, "value": d} for d in unique_diseases],
                value=unique_diseases[0],
                clearable=False,
                style={'width': '200px'}
            )
        ], style={'margin': '15px', 'float': 'right'}),

        html.Div([
            html.Label('Select the week interval:'),
            dcc.Dropdown(
                id='week-interval',
                options=[
                    {'label': '4 weeks', 'value': 4},
                    {'label': '12 weeks', 'value': 12},
                    {'label': '24 weeks', 'value': 24}
                ],
                value=4,
                style={'width': '200px'}
            )
        ], style={'margin': '20px', }),

        dcc.Graph(id='graph-with-slider'),

        html.Div([
            dcc.Slider(
                df['Year'].min(),
                df['Year'].max(),
                step=None,
                value=df['Year'].min(),
                marks={str(year): str(year) for year in df['Year'].unique()},
                id='year-slider'
            )
        ], style={'padding': '40px'})
    ])

    @callback(
        Output('graph-with-slider', 'figure'),
        [Input('year-slider', 'value'),
         Input('week-interval', 'value'),
         Input('disease-dropdown', 'value')])
    def update_figure(selected_year, week_interval, selected_disease):
        # Filtrar por doença e ano
        filtered_df = df[(df['Year'] == selected_year) & (df['Disease'] == selected_disease)]

        # Agrupar por intervalo de semanas
        filtered_df['Week_Group'] = (filtered_df['Week'] - 1) // week_interval * week_interval + 1
        grouped_df = filtered_df.groupby('Week_Group')['Cases'].sum().reset_index()

        # Criar labels para o eixo x
        grouped_df['Week_Label'] = grouped_df['Week_Group'].apply(
            lambda x: f"Weeks {x}-{min(x + week_interval - 1, 52)}"
        )

        # Calcular APC e slope
        apcs, slopes = calculate_apc_for_window(grouped_df['Cases'].values)
        grouped_df['APC'] = apcs
        grouped_df['Slope'] = slopes

        # Criar gráfico
        fig = px.line(grouped_df, 
                      x="Week_Label", 
                      y="Cases",
                      title=f"{selected_disease} Cases by {week_interval}-week intervals in {selected_year}",
                      labels={"Week_Label": "Week Interval", 
                              "Cases": "Confirmed Cases"},
                      markers=True,
                      hover_data={'APC': ':.2f', 'Slope': ':.4f'})

        # Adicionar anotações para APC e slope
        for index, row in grouped_df.iterrows():
            if row['APC'] != 0:
                fig.add_annotation(
                    x=row['Week_Label'],
                    y=row['Cases'],
                    text=f"APC: {row['APC']:.2f}%<br>Slope: {row['Slope']:.4f}",
                    showarrow=True,
                    arrowhead=1,
                    font=dict(size=10, color="black"),
                    bgcolor="white",
                    bordercolor="black",
                    borderwidth=1
                )

        fig.update_layout(
            transition_duration=500,
            xaxis_title="Week Interval",
            yaxis_title="Number of Confirmed Cases",
            yaxis_tickformat='0.1s',
            hovermode='x unified',
            plot_bgcolor='#E6FFE6',
            hoverlabel=dict(
                bgcolor="#006B2D",
                font=dict(color="white"),
            )
        )

        return fig
    
    return app

def main():
    df_data = get_notification_data()
    if df_data is None:
        print("Falha ao buscar dados do banco de dados")
        return

    df = process_data(df_data)
    if df is None:
        print("Falha ao processar dados")
        return

    app = create_dash_app(df)
    app.run(debug=True, port=8050)

if __name__ == "__main__":
    main()