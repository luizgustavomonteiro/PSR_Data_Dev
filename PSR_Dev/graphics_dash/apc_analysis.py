import os
import sys
import django
import numpy as np
from scipy.stats import linregress
import logging
import pandas as pd
from datetime import datetime
from IPython.display import display, HTML

# Add the project root directory to Python path
sys.path.append("C:\\Dev\\PSR_Data_Dev\\PSR_Dev")

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PSR_Dev.settings")

# Initialize Django
django.setup()

from myapp.models import Diseases, Regions, Notifications

class DiseaseAnalyzer:
    def handle(self, *args, **kwargs):
        try:
            # Lista todas as doenças disponíveis
            diseases = Diseases.objects.all()
            print("Available diseases:")
            for disease in diseases:
                print(f"ID: {disease.disease_id}, Name: {disease.disease_name}")
            
            # Solicita ao usuário escolher uma doença
            disease_id = int(input("Enter the ID of the disease you want to analyze: "))
            
            try:
                disease = Diseases.objects.get(disease_id=disease_id)
                disease_name = disease.disease_name
                print(f"Analyzing data for disease: {disease_name} (ID: {disease_id})")
            except Diseases.DoesNotExist:
                print(f"Disease with ID {disease_id} does not exist.")
                return None
                
            # Filtra por disease_id
            data = Notifications.objects.filter(disease_id=disease_id).values(
                'notification_id', 'disease', 'region',
                'notification_week', 'notification_year',
                'cases_confirmed'
            )

            # Convert to DataFrame
            df_data = pd.DataFrame(data)
            
            # Verifica se existem dados para a doença selecionada
            if df_data.empty:
                print(f"No data available for the selected disease (ID: {disease_id})")
                return None
                
            print(df_data)

            # Group data by year and week, summing up confirmed cases
            sum_case_week = df_data.groupby(['notification_year', 'notification_week'])['cases_confirmed'].sum().reset_index()
            sum_case_week.rename(columns={
                'notification_year': 'Year',
                'notification_week': 'Week',
                'cases_confirmed': 'Cases'
            }, inplace=True)

            # Display all rows of the DataFrame
            pd.set_option('display.max_rows', None)
            print(sum_case_week)

            # Use the select_interval function (mantendo original)
            joinpoints = self.select_interval(sum_case_week)
            print("Joinpoints (interval groups):")
            for idx, group in enumerate(joinpoints, 1):
                print(f"Interval {idx}:")
                print(group)

            # Calculate APC for each segment
            limit_apc = 20  # Set an example APC limit
            results = self.calculate_apc(joinpoints, limit_apc)

            # Display results
            if results is not None:
                # Adiciona informações da doença aos resultados
                results['Disease'] = disease_name
                results['Disease ID'] = disease_id
                display(HTML(results.to_html(index=False)))
            else:
                print("No results to display.")
                
            return results
            
        except Exception as e:
            print(f"Error in analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    # Select Interval (Joinpoints) Function - mantido como no original
    def select_interval(self, df):
        while True:
            try:
                interval = int(input("Choose a week interval (4, 12, 24): "))
                if interval in [4, 12, 24]:
                    num_joinpoints = len(df) // interval
                    joinpoints = [df.iloc[i * interval:(i + 1) * interval] for i in range(num_joinpoints)]
                    # Handle leftover rows
                    if len(df) % interval != 0:
                        joinpoints.append(df.iloc[num_joinpoints * interval:])
                    return joinpoints
                else:
                    print("Please, choose a valid interval (4, 12, 24).")
            except ValueError:
                print("Please, choose an integer value.")

    # APC Calculation Function - com tratamento de casos zero
    def calculate_apc(self, segments, limit_apc):
        results = []
        for i, segment in enumerate(segments):
            if len(segment) > 1:
                x = np.arange(len(segment))
                
                # Adiciona tratamento para casos zero
                cases = segment['Cases'].values
                cases = np.where(cases == 0, 0.01, cases)  # Substitui zeros por 0.01 para evitar log(0)
                y = np.log(cases)

                # Perform linear regression
                slope, intercept, r_value, p_value, std_err = linregress(x, y)
                apc = (np.exp(slope) - 1) * 100  # APC calculation
                duration = segment['Week'].iloc[-1] - segment['Week'].iloc[0] + 1

                # Warning if APC surpasses the limit
                if apc > limit_apc:
                    print(f"Alert! APC in segment {i + 1} surpassed the limit of {limit_apc}% with a value of {apc:.2f}%.")

                # Add results to the list
                results.append({
                    'Segment': f'Segment {i + 1}',
                    'Slope Log': slope,
                    'APC (%)': apc,
                    'Intercept': intercept,
                    'R-squared': r_value ** 2,
                    'P-value': p_value,
                    'Std Err': std_err,
                    'Start Week': segment['Week'].iloc[0],
                    'End Week': segment['Week'].iloc[-1],
                    'Start Year': segment['Year'].iloc[0],
                    'End Year': segment['Year'].iloc[-1],
                    'Cases Start': segment['Cases'].iloc[0],
                    'Cases End': segment['Cases'].iloc[-1],
                    'Duration': duration
                })

        if results:
            # Convert results into a DataFrame
            df_results = pd.DataFrame(results)
            print(df_results)
            return df_results
        else:
            print("No segments with sufficient data.")
            return None

def main():
    analyzer = DiseaseAnalyzer()
    analyzer.handle()

if __name__ == "__main__":
    main()