import pandas as pd
import numpy as np
import json
from datetime import datetime
import requests # IMPORTANTE: Adicionado para fazer o request real!
import oracledb # IMPORTANTE: Trocado de cx_Oracle para oracledb

# Caminhos locais dentro do container do Airflow para armazenamento temporário
RAW_GEO_PATH = '/opt/airflow/dags/satelite_raw.json'
CLEAN_GEO_PATH = '/opt/airflow/dags/satelite_clean.csv'

def extrair_dados_satelite():
    """
    Etapa 1 e 2: Coleta dados REAIS de clima e superfície (Open-Meteo API).
    Fazendo um request real sem precisar de conta ou chaves de acesso.
    """
    print("Iniciando requisição REAL para a API pública de clima/satélite...")
    
    # Coordenadas reais de diferentes zonas de São Paulo
    coordenadas = [
        {"cidade": "Sao Paulo - Centro", "lat": -23.5505, "lon": -46.6333},
        {"cidade": "Sao Paulo - Paulista", "lat": -23.5615, "lon": -46.6560},
        {"cidade": "Sao Paulo - Itaquera", "lat": -23.5350, "lon": -46.4674},
        {"cidade": "Sao Paulo - Morumbi", "lat": -23.6001, "lon": -46.7200},
        {"cidade": "Sao Paulo - Ibirapuera", "lat": -23.5874, "lon": -46.6576}
    ]
    
    grid_dados = []
    
    # Faz o request real para cada coordenada
    for local in coordenadas:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={local['lat']}&longitude={local['lon']}&current=temperature_2m"
        response = requests.get(url)
        
        if response.status_code == 200:
            dados_api = response.json()
            temp_real = dados_api['current']['temperature_2m']
            
            # Converte a temperatura em um índice de calor/densidade (0 a 100)
            indice_calor = int((temp_real / 40) * 100) 
            
            grid_dados.append({
                "cidade": local["cidade"],
                "latitude": local["lat"],
                "longitude": local["lon"],
                "indice_densidade": indice_calor,
                "data_registro": datetime.now().strftime("%Y-%m-%d")
            })
        else:
            print(f"Erro na API para {local['cidade']}")

    # Armazenamento Temporário do JSON Bruto
    with open(RAW_GEO_PATH, 'w') as f:
        json.dump(grid_dados, f)
    print("Dados brutos extraídos da API real com sucesso!")

def transformar_dados_satelite():
    """
    Etapa 3: Tratamento, limpeza e enriquecimento com Pandas.
    """
    print("Iniciando a transformação dos dados geoespaciais...")
    
    with open(RAW_GEO_PATH, 'r') as f:
        dados = json.load(f)
        
    df = pd.DataFrame(dados)
    df['indice_densidade'] = df['indice_densidade'].fillna(0)
    
    condicoes = [
        (df['indice_densidade'] >= 80),
        (df['indice_densidade'] >= 50) & (df['indice_densidade'] < 80),
        (df['indice_densidade'] < 50)
    ]
    categorias = ['ZONA CRITICA - ALTA DENSIDADE', 'ZONA ADIACENTE - MEDIA DENSIDADE', 'ZONA DISPERSA - BAIXA DENSIDADE']
    df['classificacao_zona'] = np.select(condicoes, categorias, default='IGNORADO')
    
    df.to_csv(CLEAN_GEO_PATH, index=False)
    print(f"Transformação concluída. {len(df)} registros processados.")

def carregar_dados_oracle():
    """
    Etapa 4: Carga estruturada no Oracle Database usando a biblioteca nova.
    """
    print("Iniciando conexão com o Oracle Database da FIAP...")
    df = pd.read_csv(CLEAN_GEO_PATH)
    
    dsn_tns = oracledb.makedsn(host='oracle.fiap.com.br', port=1521, sid='ORCL')
    
    connection = oracledb.connect(user='rm551717', password='150504', dsn=dsn_tns)
    cursor = connection.cursor()
    
    print("Inserindo registros na tabela T_SATELITE_URBANO...")
    for index, row in df.iterrows():
        sql = """
            INSERT INTO T_SATELITE_URBANO (cidade, latitude, longitude, indice_densidade, classificacao_zona, data_satelite)
            VALUES (:1, :2, :3, :4, :5, TO_DATE(:6, 'YYYY-MM-DD'))
        """
        cursor.execute(sql, (
            row['cidade'], 
            float(row['latitude']), 
            float(row['longitude']), 
            int(row['indice_densidade']), 
            row['classificacao_zona'], 
            row['data_registro']
        ))
        
    connection.commit()
    cursor.close()
    connection.close()
    print("Carga no Oracle finalizada com sucesso!")