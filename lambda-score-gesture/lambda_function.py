import json
import boto3
import os

endpoint_dashboard = os.environ.get('endpoint_dashboard')

def lambda_handler(event, context):
    print('event: ', event)
    
    userId = event["userId"]
    requestId = event["requestId"]
    type = event["type"]
    text = event["text"]
    
    # To-Do: Get Score
    # send the score to the dashboard    
    if type=='gesture':
        if text == "heart":
            score = 5
        else:
            score = 1    
    print('score: ', score)
    
    # To-do: Push the text for the last message
    
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps({        
            "userId": userId,
            "requestId": requestId,
            "score": score
        })
    }
