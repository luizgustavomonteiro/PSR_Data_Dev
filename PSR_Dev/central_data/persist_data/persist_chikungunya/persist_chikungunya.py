import os
import sys
import django


# Add the project root directory to Python path
sys.path.append("C:\\Dev\\PSR_Data_Dev\\PSR_Dev")


# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PSR_Dev.settings")

# Initialize Django
django.setup()


import logging
import pandas as pd
from myapp.models import Diseases, Regions, Notifications
from datetime import datetime

# Configuração do logging
log_file_path = "C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\central_data\\download_data\\download_logs\\chikungunya\\chikungunya_application_stage.log"
stage_log_path = "C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\central_data\\download_data\\download_logs\\chikungunya\\chikungunya_download_historical.txt"


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def read_data(file_path):
    try:
        # Lê o arquivo CSV com separador ";"
        data = pd.read_csv(file_path, sep=';')
        return data
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return None

def process_data(data):
    # Verifica se a coluna "Semana epidem. notificação" existe
    if "Semana epidem. notificação" not in data.columns:
        logger.error("Missing column: 'Semana epidem. notificação'")
        return None

    # Renomeia a coluna "Semana epidem. notificação" para "Week"
    data.rename(columns={"Semana epidem. notificação": "Week"}, inplace=True)

    # Substitui valores '-' por 0
    data.replace('-', 0, inplace=True)

    # Converte as colunas de casos para numérico, tratando erros
    # O melt vai "derreter" as colunas de região em uma nova coluna chamada "Region"
    df_long = data.melt(id_vars=["Week"], var_name="Region", value_name="Cases_Confirmed")
    
    # Converte a coluna de casos confirmados para int, se possível
    df_long['Cases_Confirmed'] = pd.to_numeric(df_long['Cases_Confirmed'], errors='coerce').fillna(0).astype(int)
    
    # Extrai números da semana para garantir que a coluna 'Week' tenha formato correto
    df_long['Week'] = df_long['Week'].str.extract(r'(\d+)').astype(int)

    return df_long

def save_to_database(df_long, file_path):
    # Extrai o nome da doença e o ano do nome do arquivo
    try:
        disease_name = os.path.basename(file_path).split('_')[0]
        year = int(os.path.basename(file_path).split('_')[1].split('.')[0])

        # Cria ou obtém a doença
        disease, _ = Diseases.objects.get_or_create(disease_name=disease_name)
        
        # Itera sobre cada linha do dataframe e salva os dados no banco
        for _, row in df_long.iterrows():
            region, _ = Regions.objects.get_or_create(region_name=row["Region"])
            Notifications.objects.create(
                notification_week=row["Week"],  
                notification_year=year,
                cases_confirmed=row["Cases_Confirmed"],
                deaths_confirmed=0,
                disease=disease,  
                region=region      
            )

            # Log de dados salvos
            logger.info(
                f"Saved data: Year {year}, Week {row['Week']}, Region {row['Region']}, Confirmed Cases {row['Cases_Confirmed']}"
            )
    except Exception as e:
        logger.error(f"Error saving data to the database: {e}")

def main(folder, base_name):
    current_year = datetime.now().year
    
    # Monta os nomes dos últimos 3 anos
    files = [f"{base_name}_{year}.csv" for year in range(current_year, current_year - 3, -1)]
    files_paths = [os.path.join(folder, file) for file in files]

    for file_path in files_paths:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            continue

        logger.info(f"Processing file: {file_path}")
        data = read_data(file_path)

        if data is not None:
            logger.info(f"File read successfully: {file_path}")
            logger.info(f"First five rows:\n{data.head()}")
            df_long = process_data(data)
            save_to_database(df_long, file_path)
        else:
            logger.error(f"Failed to process file: {file_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Import multiple CSV files for database')
    parser.add_argument(
        '--folder', 
        type=str, 
        default='C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\central_data\\source_data\\chikungunya',
        help='Folder that contains CSV files'
    )
    parser.add_argument(
        '--base_name', 
        type=str, 
        default='Chikungunya',
        help='Base name of the files (e.g., Chikungunya)'
    )

    args = parser.parse_args()

    main(args.folder, args.base_name)