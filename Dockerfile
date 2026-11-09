FROM apache/airflow:2.10.5-python3.11
RUN pip install --no-cache-dir apache-airflow==2.10.5 astronomer-cosmos==1.9.0 statsd==4.0.1 pymssql==2.3.2 boto3==1.35.99 'psycopg[binary]==3.2.4' requests==2.32.4 \
    && python -m venv /opt/airflow/dbt-venv \
    && /opt/airflow/dbt-venv/bin/pip install --no-cache-dir dbt-core==1.9.8 dbt-postgres==1.9.0
ENV PYTHONPATH=/opt/airflow/project
COPY --chown=airflow:root . /opt/airflow/project
