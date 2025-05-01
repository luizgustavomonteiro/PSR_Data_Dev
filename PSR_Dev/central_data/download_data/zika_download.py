import logging
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

# Logging Settings
# To storage each stage of selenium application
log_file_path = "C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\central_data\\download_data\\download_logs\\zika\\zika_application_stage.log"
stage_log_path = "C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\central_data\\download_data\\download_logs\\zika\\zika_download_historical.txt"


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

class DataDownloader:
    def __init__(self, file_name):
        self.download_dir = "C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\central_data\\source_data\\zika"
       
        self.file_name = file_name
        self.new_file_name = file_name # Name of new file CSV

        chrome_options = Options()
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "directory_upgrade": True,
            "safebrowsing.enabled": True
        }

        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

    # Page access
    def page_access(self, url):
        try:
            self.driver.get(url)
            logging.info(f'Accessing {url}')
        except Exception as e:
            logging.error(f"Error accessing {url}: {e}")

    # Function to select page options
    def select_option(self, dropdown_id, value, option_type="Option"):
        try:
            dropdown = self.wait.until(EC.element_to_be_clickable((By.ID, dropdown_id)))
            select = Select(dropdown)
            if select.is_multiple:
                select.deselect_all()
            select.select_by_value(value)
            logging.info(f"{option_type} selected: {select.first_selected_option.text}")
        except TimeoutException:
            logging.error(f"Timeout to find {option_type} option: {value}")
        except Exception as e:
            logging.error(f"Error selecting {option_type} option {value}: {e}")

    # Function to select year option
    def select_year_option(self, dropdown_id, value, option_type="Option"):
        try:
            dropdown = self.wait.until(EC.element_to_be_clickable((By.ID, dropdown_id)))
            select = Select(dropdown)
            if select.is_multiple:
                select.deselect_all()
            select.select_by_visible_text(value)

            logging.info(f"{option_type} selected: {select.first_selected_option.text}")
        except TimeoutException:
            logging.error(f"Timeout to find {option_type} option: {value}")
        except Exception as e:
            logging.error(f"Error selecting {option_type} option {value}: {e}")

    # Function to click option to download
    def click_button(self, button_name):
        try:
            mostra_button = self.wait.until(EC.element_to_be_clickable((By.NAME, button_name)))
            mostra_button.click()
            logging.info(f"Button '{button_name}' clicked successfully!")
        except TimeoutException:
            logging.error(f"Timeout to find button: {button_name}")
        except Exception as e:
            logging.error(f"Error clicking button {button_name}: {e}")


    # Function to switch table as the mapping does
    def switch_to_new_tab(self):
        try:
            self.wait.until(lambda driver: len(driver.window_handles) > 1)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            logging.info("Switched to new tab.")
        except Exception as e:
            logging.error(f"Error switching to new tab: {e}")

    # Function to click the download button
    def download_csv(self, xpath):
        try:

            csv_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            csv_button.click()
            logging.info("CSV file download initiated.")
            time.sleep(20)

            # Armazenar o nome do arquivo baixado
            csv_files = [f for f in os.listdir(self.download_dir) if f.endswith('.csv')]
            if csv_files:
                self.original_file_name = csv_files[0]
        except TimeoutException:
            logging.error("Timeout to find CSV button.")
        except Exception as e:
            logging.error(f"Error downloading CSV file: {e}")

    # Function to rename downloaded file
    def rename_downloaded_file(self, year):
        try:
        # Aguarda o download ser concluído
            time.sleep(10)

        # Lista os arquivos CSV no diretório de download
            csv_files = [f for f in os.listdir(self.download_dir) if f.endswith('.csv')]
            csv_files.sort(key=lambda f: os.path.getmtime(os.path.join(self.download_dir, f)), reverse=True)

            if csv_files:
                most_recent_file = csv_files[0]
                old_file_path = os.path.join(self.download_dir, most_recent_file)
                new_file_name = f"{self.file_name}_{year}.csv"
                new_file_path = os.path.join(self.download_dir, new_file_name)

            # Verifica se o arquivo foi baixado recentemente (últimos 30 segundos)
                if time.time() - os.path.getmtime(old_file_path) < 30:
                # Remove o arquivo existente se o nome final já estiver em uso
                    if os.path.exists(new_file_path):
                        os.remove(new_file_path)
                        logging.info(f"Arquivo existente '{self.new_file_name}' removido.")

                # Renomeia o arquivo baixado para o nome final
                    os.rename(old_file_path, new_file_path)
                    logging.info(f"Arquivo renomeado de '{most_recent_file}' para '{self.new_file_name}'")
                else:
                    logging.warning(f"Nenhum arquivo novo encontrado para renomear. Arquivo mais recente: '{most_recent_file}'")
            else:
                logging.warning("Nenhum arquivo CSV encontrado para renomear.")
        except Exception as e:
            logging.error(f"Erro ao renomear o arquivo baixado: {e}")

    # Function to close driver
    def close(self):
        self.driver.quit()
        logging.info("Driver closed successfully.")

    # function to save download stage
    def save_stage(self, stage_name):
        with open(stage_log_path, 'a') as log_file:
            log_file.write(f"{stage_name} completed at {time.ctime()}\n")
        logging.info(f"Stage {stage_name} saved.")

def main():
    downloader = DataDownloader("zika")

    url = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sinannet/cnv/zikamt.def"
    csv_button_xpath = "/html/body/div/div/div[3]/table/tbody/tr/td[1]/a"

    try:
        
        current_year = datetime.now().year
        for year in range(current_year, current_year -3, -1):
            downloader.page_access(url)
            downloader.select_option('L', 'Semana_epidem._notificação', "Line")
            downloader.select_option('C', 'UF_de_notificação', "Column")
            downloader.select_option('I', 'Casos_Prováveis', "Content")
            downloader.select_year_option('A', str(year), "Year") # Change it to integer
            downloader.click_button('mostre')
            downloader.switch_to_new_tab()
            downloader.download_csv(csv_button_xpath)
            downloader.rename_downloaded_file(year)
            downloader.save_stage("Download for year {year}")

    except Exception as e:
        logging.error(f"An error occurred during the download process: {e}")

    finally:
        downloader.close()

if __name__ == "__main__":
    main()