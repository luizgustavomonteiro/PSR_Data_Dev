import pandas as pd

from datetime import datetime


class CleanFile:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None

    def load_csv(self, skiprows=3, skipfooter=10):
        try:
            self.data = pd.read_csv(
                self.file_path,
                sep=';',
                encoding = 'latin-1',
                skiprows=skiprows,
                skipfooter=skipfooter,
                engine='python'
            )
            print(f"File {self.file_path} Loaded Succesfully!" )

        except FileNotFoundError:
            print(f"File {self.file_path} not found")
        except Exception as e:
            print(f"Error loading file {self.file_path}: {e}")

    def drop_from_text(self, reference_text):
        if self.data is not None:
            # Encontrar o índice da primeira ocorrência do texto de referência
            index_to_drop = self.data[self.data.apply(lambda row: row.astype(str).str.contains(reference_text, na=False).any(), axis=1)].index
            
            if not index_to_drop.empty:
                # Dropar todas as linhas a partir do índice encontrado
                self.data = self.data.iloc[:index_to_drop[0]]
                print(f"Lines from the first occurrence of '{reference_text}' have been removed.")
            else:
                print(f"No line contains the text '{reference_text}'.")
        else:
            print("No data to show")

    def drop_column_from_text(self, reference_text):
        if self.data is not None:
        # Encontrar as colunas que contêm o texto de referência
            columns_to_drop = [col for col in self.data.columns if reference_text in col]
        
            if columns_to_drop:
            # Dropar as colunas encontradas
                self.data = self.data.drop(columns=columns_to_drop)
                print(f"Columns containing the text '{reference_text}' have been removed: {columns_to_drop}.")
            else:
                print(f"No columns contain the text '{reference_text}'.")
        else:
            print("No data to show.")


    def show_head(self, n=55):
        if self.data is not None:
            print(self.data.head(n).to_string(index=False))
        else:
            print("No data to show")

    def save_to_csv(self, output_file_path):
        if self.data is not None:
            self.data.to_csv(output_file_path, index=False, sep=';')
            print(f"Data saved to {output_file_path}")
        else:
            print("No data to save")

try:
    
    
    current_year = datetime.now().year
    years = range(current_year, current_year - 3, -1)
    base_path = 'C:\\Dev\\PSR_Data_Dev\\PSR_Dev\\central_data\\source_data\\chikungunya\\'
    

    for year in years:
        file_path = f"{base_path}Chikungunya_{year}.csv"


        open_file = CleanFile(file_path)

        open_file.load_csv()
        open_file.drop_from_text('Total')
        open_file.drop_column_from_text('Total')
        open_file.show_head()
        open_file.save_to_csv(file_path)

except Exception as e:
    print(f"Error during cleaner process file: {e}!")