from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.s3 import S3DeleteObjectsOperator, S3ListOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor


s3_bucket = 'stream-n-detect'
datalake_folder = 'datalake/'
staging_folder = 'staging/'
max_workers = 10

# define DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}
dag = DAG(
    's3_stage_for_training',
    default_args=default_args,
    description='Move data from datalake to staging in S3',
    schedule_interval=None,
    catchup=False,
)

clear_staging = S3DeleteObjectsOperator(
    task_id='clear_staging',
    bucket=s3_bucket,
    prefix=staging_folder,
    aws_conn_id='aws_default',
    dag=dag,
)

list_datalake_objects = S3ListOperator(
    task_id='list_datalake_objects',
    bucket=s3_bucket,
    prefix=datalake_folder,
    aws_conn_id='aws_default',
    dag=dag,
)

def copy_objects_to_staging(**kwargs):
    s3 = S3Hook(aws_conn_id='aws_default')
    datalake_objects = kwargs['ti'].xcom_pull(task_ids='list_datalake_objects')

    if not datalake_objects:
        raise ValueError("No objects found in the datalake folder.")
    
    def copy_object_task(obj_key):
        dest_key = obj_key.replace(datalake_folder, staging_folder, 1)
        s3.copy_object(
            source_bucket_key=obj_key,
            dest_bucket_key=dest_key,
            source_bucket_name=s3_bucket,
            dest_bucket_name=s3_bucket,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(copy_object_task, datalake_objects)
    
stage_for_training = PythonOperator(
    task_id='stage_for_training',
    python_callable=copy_objects_to_staging,
    dag=dag,
)

# task dependencies order
clear_staging >> list_datalake_objects >> stage_for_training
