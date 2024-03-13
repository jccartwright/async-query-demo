"""
second of a pair of functions demonstrating an approach to handling async Athena
queries in a Step Function. This function listens for the EventBridge event 
signaling completion of the query, and then it calls the
send_task_success/send_task_failure allowing the step function to continue
"""
import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOGLEVEL", "WARNING"))

QUERIES_TABLE = os.getenv('QUERIES_TABLE', default='athena_queries')

athena = boto3.client('athena')
dynamodb = boto3.resource('dynamodb')
stepfunction = boto3.client('stepfunctions')
s3 = boto3.resource('s3')
ddb_table = dynamodb.Table(QUERIES_TABLE)


def send_success(task_token, payload=None):
    response = stepfunction.send_task_success(
        taskToken=task_token,
        output=json.dumps(payload)
    )
    return response


def send_failure(task_token, error_code='', error_cause=''):
    response = stepfunction.send_task_failure(
        taskToken=task_token,
        error=error_code,
        cause=error_cause
    )
    return response


def is_query_of_interest(query_id):
    response = ddb_table.get_item(
        Key={'QueryExecutionId': query_id}
    )
    if 'Item' in response:
        return response
    else:
        return None


def lambda_handler(event, context):
    query_execution_id = event['detail']['queryExecutionId']

    # query DDB to see if this query is associated with a TaskToken
    query_of_interest = is_query_of_interest(query_execution_id)

    if not query_of_interest:
        logger.debug(f'query id {query_execution_id} is not of interest')
        return

    item = query_of_interest['Item']
    task_token = item['TaskToken']
    query_id = item['QueryExecutionId']
    payload = {
        "QueryExecution": {
            "QueryExecutionId": query_id
        }
    }
    send_success(task_token, payload)

    # EventBridge rule event pattern only allows 'SUCCEEDED' and 'FAILED'
    if event['detail']['currentState'] != 'SUCCEEDED':
        logger.warning(f"Failed query: {query_execution_id}")
        send_failure(task_token, error_code='1', error_cause='athena query failed')

    return

# {
#     'version': '0',
#     'id': 'ddd2dae3-39d2-7ebf-6066-38df6a7176bb',
#     'detail-type': 'Athena Query State Change',
#     'source': 'aws.athena',
#     'account': '282856304593',
#     'time': '2023-03-09T00:26:04Z',
#     'region': 'us-east-1',
#     'resources': [],
#     'detail': {
#         'currentState': 'SUCCEEDED',
#         'previousState': 'RUNNING',
#         'queryExecutionId': '2b1a5ee0-a30e-490a-b50e-d06a2c8ff1f5',
#         'sequenceNumber': '3',
#         'statementType': 'DML',
#         'versionId': '0',
#         'workgroupName': 'primary'
#     }
# }
