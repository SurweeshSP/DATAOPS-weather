from airflow import DAG
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decorators import task
from datetime import datetime, timedelta

LAT = 51.5074
LONG = -0.1278
POSTGRES_CONN_ID = 'postgres_default'
API_CONN_ID = 'open_meteo_api'

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 8, 14)  # fixed date for reproducibility
}

with DAG(
    dag_id='weather_pipeline',
    default_args=default_args,
    schedule='@daily',
    catchup=False
) as dag:

    @task()
    def create_table():
        postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS weather_data (
                id SERIAL PRIMARY KEY,
                latitude DECIMAL(9, 6) NOT NULL,
                longitude DECIMAL(9, 6) NOT NULL,
                temperature DECIMAL(5, 2),
                windspeed DECIMAL(5, 2),
                winddirection INTEGER,
                weathercode INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        postgres_hook.run(create_table_sql)

    @task()
    def extract_data():
        http_hook = HttpHook(http_conn_id=API_CONN_ID, method='GET')
        endpoint = f"/v1/forecast?latitude={LAT}&longitude={LONG}&current_weather=true"
        res = http_hook.run(endpoint)
        if res.status_code == 200:
            return res.json()
        else:
            raise Exception(f"Error fetching data: {res.text}")

    @task()
    def transform_data(data):
        current_weather = data.get('current_weather', {})
        return {
            'latitude': LAT,
            'longitude': LONG,
            'temperature': current_weather.get('temperature'),
            'windspeed': current_weather.get('windspeed'),
            'winddirection': current_weather.get('winddirection'),
            'weathercode': current_weather.get('weathercode')
        }

    @task()
    def load_data(transformed_data):
        postgres_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        insert_sql = """
            INSERT INTO weather_data (latitude, longitude, temperature, windspeed, winddirection, weathercode, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        postgres_hook.run(
            insert_sql,
            parameters=(
                transformed_data['latitude'],
                transformed_data['longitude'],
                transformed_data['temperature'],
                transformed_data['windspeed'],
                transformed_data['winddirection'],
                transformed_data['weathercode']
            )
        )

    # Define task dependencies
    create_table_task = create_table()
    data = extract_data()
    processed = transform_data(data)
    
    # Set up the pipeline
    create_table_task >> data >> processed >> load_data(processed)