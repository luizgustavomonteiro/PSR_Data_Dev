import os
import django
import sys
import pandas as pd
from django.db.models import Sum
import json
import plotly.express as px
import plotly.graph_objects as go

# Add the project root directory to Python path
sys.path.append("C:\\Dev\\PSR_Data_Dev\\PSR_Dev")

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PSR_Dev.settings")

django.setup()

from myapp.models import Diseases, Regions, Notifications

# Obtém todos os anos disponíveis
available_years = sorted(Notifications.objects.values_list('notification_year', flat=True).distinct())

# Obtém todas as doenças do banco
diseases = Diseases.objects.values_list("disease_name", flat=True)


# Carrega o arquivo GeoJSON do Brasil
brazil_states_path = 'C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\myapp\\static\\json\\brazil_estados.geojson'

with open(brazil_states_path, 'r') as f:
    brazil_states = json.load(f)

# Dicionário para armazenar dados de cada doença e ano
disease_year_data = {}

for disease in diseases:
    disease_year_data[disease] = {}
    for year in available_years:
        # Consulta que filtra pelo ano e doença, junta Notifications com Diseases e Regions
        data = Notifications.objects.filter(
            disease__disease_name=disease,
            notification_year=year
        ).values("region__region_name") \
          .annotate(total_cases=Sum("cases_confirmed")) \
          .order_by('-total_cases')

        df = pd.DataFrame(list(data))
        
        # Adiciona os dados ao dicionário
        disease_year_data[disease][year] = df

# 🔹 Cria a figura inicial para a primeira doença e primeiro ano
first_disease = diseases[0]
first_year = available_years[0]
df_first = disease_year_data[first_disease][first_year]

fig = px.choropleth(
    df_first, 
    geojson=brazil_states, 
    locations='region__region_name',  
    featureidkey="properties.uf_05", 
    color='total_cases',
    color_continuous_scale=px.colors.sequential.Mint,
    labels={'total_cases': 'Casos Confirmados'}
)

fig.update_geos(visible=False, fitbounds="locations")

# 🔹 Adiciona os dropdowns para trocar doenças e anos
disease_buttons = []
for disease in diseases:
    disease_buttons.append(
        dict(
            label=disease,
            method="update",
            args=[
                {"z": [disease_year_data[disease][first_year]["total_cases"]], 
                 "locations": [disease_year_data[disease][first_year]["region__region_name"]]},
                {"title": f"Casos Confirmados - {disease} ({first_year})"}
            ]
        )
    )

year_buttons = []
for year in available_years:
    year_buttons.append(
        dict(
            label=str(year),
            method="update",
            args=[
                {"z": [disease_year_data[first_disease][year]["total_cases"]], 
                 "locations": [disease_year_data[first_disease][year]["region__region_name"]]},
                {"title": f"Casos Confirmados - {first_disease} ({year})"}
            ]
        )
    )

fig.update_layout(
    updatemenus=[
        dict(buttons=disease_buttons, direction="down", showactive=True, x=0.1, y=1.15),
        dict(buttons=year_buttons, direction="down", showactive=True, x=0.3, y=1.15)
    ],
    title=f"Casos Confirmados - {first_disease} ({first_year})"
)

# 🔹 Salva o gráfico como HTML interativo
output_path = 'C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\myapp\\static\\html\\brazil_states.html'

fig.write_html(output_path)

print(f'Arquivo salvo em {output_path}')
print(f'Anos disponíveis: {available_years}')
print(f'Doenças disponíveis: {list(diseases)}')