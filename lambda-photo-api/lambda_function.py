import json
import boto3
import os
from urllib import parse
import uuid

s3_photo_prefix = os.environ.get('s3_photo_prefix')
path = os.environ.get('path')        
sqsUrl = os.environ.get('sqsUrl')
sqs_client = boto3.client('sqs')

def lambda_handler(event, context):
    print('event: ', event)
    
    requestId = event["requestId"]
    print('requestId: ', requestId)

    bucket = event["bucket"]   
    key = event["key"]   

    # get filename
    if "id" in event:
        id = event["id"]
    else:
        id = key.split('/')[-1].split('.')[0]
    
    # ext
    ext = key.split('.')[-1]
    if ext == 'jpg':
        ext = 'jpeg'
    
    url_original = path+parse.quote(key)
    print('url_original: ', url_original)
        
    generated_urls = []    
    for index in range(3):
        object_name = f'photo_{id}_{index+1}.{ext}'
    
        url = path+s3_photo_prefix+'/'+parse.quote(object_name)
        print('url: ', url)
        
        generated_urls.append(url)
        
    # message
    message = {
        'requestId': requestId,
        'bucket': bucket,
        'key': key
    }
    
    eventId = str(uuid.uuid1())
    print('eventId: ', eventId)
    
    # push to SQS
    try:
        print('sqsUrl: ', sqsUrl)            
            
        sqs_client.send_message(  # fifo
            QueueUrl=sqsUrl, 
            MessageAttributes={},
            MessageDeduplicationId=eventId,
            MessageGroupId="photoApi",
            MessageBody=json.dumps(message)
        )
        print('Successfully push the queue message: ', json.dumps(message))
            
    except Exception as e:
        print('Fail to push the queue message: ', e)
    
    result = {            
        "url_original": url_original,
        "url_generated": json.dumps(generated_urls)
    }
    print('result: ', result)
            
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps(result)
    }
