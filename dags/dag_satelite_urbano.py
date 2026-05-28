from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Importa as funções criadas no arquivo satelite_pipeline.py
from satelite_pipeline import extrair_dados_satelite, transformar_dados_satelite, carregar_dados_oracle

# Configurações padrão da DAG
default_args = {
    'owner': 'Equipe_SatUrbano',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

# Declaração do fluxo orquestrado
with DAG(
    'pipeline_satelite_densidade_urbana',
    default_args=default_args,
    description='Pipeline de monitoramento de densidade urbana via satélite para mobilidade humana',
    schedule='@weekly', # Execução semanal programada automaticamente
    catchup=False,
) as dag:

    task_extract = PythonOperator(
        task_id='extrair_dados_satelite_api',
        python_callable=extrair_dados_satelite,
    )

    task_transform = PythonOperator(
        task_id='tratar_e_categorizar_densidade',
        python_callable=transformar_dados_satelite,
    )

    task_load = PythonOperator(
        task_id='carregar_dados_no_oracle',
        python_callable=carregar_dados_oracle,
    )

    # Definição das dependências lógicas (Grafo Direcionado Acíclico)
    task_extract >> task_transform >> task_load