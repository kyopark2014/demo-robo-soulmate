import json
import boto3
import os

endpoint_dashboard = os.environ.get('endpoint_dashboard')

def lambda_handler(event, context):
    # print('event: ', event)
    
    body = event["body"]
    jsonBody = json.loads(body)

    user_id = jsonBody["userId"]
    request_id = jsonBody["requestId"]
    type = jsonBody["type"]
    text = jsonBody["text"]
    
    # To-Do: Get Score
    # send the score to the dashboard    
    if text:
        score = 5
    else:
        score = 1    
    print('score: ', score)
    
    # To-do: Push the text for the last message
    
    return {
        'statusCode': 200,
        'info': json.dumps({
            'score': score
        })
    }
