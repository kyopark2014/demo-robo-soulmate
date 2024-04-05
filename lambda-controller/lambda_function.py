import json
import boto3
import os

def lambda_handler(event, context):
    print('event: ', event)
    
    control = event['control']
    print('control: ', control)

    return {
        'statusCode': 200,
        'info': json.dumps({
            'result': 'success'
        })
    }
