"""
first of a pair of functions demonstrating an approach to handling async Athena
queries in a Step Function. Step function calls this function passing a taskToken.
This function initiates a query but does NOT call back to the step function. A
second function listens for the EventBridge event signaling the completion of
the query, and it sends calls the send_task_success/send_task_failure
"""
import json
import random
import time
import boto3
import os

# TODO take as event parameters
DATABASE = 'dcdb'
TABLE = 'csb_parquet'
S3_OUTPUT = 's3://csb-pilot-delivery/'
QUERIES_TABLE = os.getenv('QUERIES_TABLE', default='athena_queries')

athena = boto3.client('athena')
dynamodb = boto3.resource('dynamodb')
ddb_table = dynamodb.Table(QUERIES_TABLE)


def insert_query_id(id, task_token):
    # expire records 1 hour after creation
    ttl = int(time.time()) + (1 * 60 * 60)
    attributes = {
        'QueryExecutionId': id,
        'TaskToken': task_token,
        'TTL': ttl
    }
    response = ddb_table.put_item(
        Item=attributes
    )
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception('insert into database failed')
    return attributes


def lambda_handler(event, context):
    # print(event)
    task_token = event['MyTaskToken']

    # Database specified in Execution Context below.
    # query = f"select h3_hires, count(*) from {DATABASE}.{TABLE} group by 1 order by 1"
    query = f"select h3, count(*) from {DATABASE}.{TABLE} group by 1 order by 1"

    # Execution
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': DATABASE
        },
        ResultConfiguration={
            'OutputLocation': S3_OUTPUT
        }
    )

    # get query execution id
    query_execution_id = response['QueryExecutionId']
    # print(response)
    # query_status = athena.get_query_execution(QueryExecutionId=query_execution_id)
    # query_execution_status = query_status['QueryExecution']['Status']['State']
    insert_query_id(id=query_execution_id, task_token=task_token)

    return response
