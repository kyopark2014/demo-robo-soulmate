import json
import boto3
import os
from urllib import parse
import uuid
import traceback

s3_photo_prefix = os.environ.get('s3_photo_prefix')
bucketName = os.environ.get('bucketName')        
path = os.environ.get('path')        
sqsUrl = os.environ.get('sqsUrl')
sqs_client = boto3.client('sqs')

tableName = 'EmotionDetailInfo-3d2nq2n4sfcqnfelmjj3n3ycje-dev'

def lambda_handler(event, context):
    print('event: ', event)
    
    requestId = event["requestId"]
    print('requestId: ', requestId)

    dynamodb_client = boto3.client('dynamodb')
    try:
        resp = dynamodb_client.scan(
            TableName=tableName
        )
        print('resp: ', resp)
    except Exception as ex:
        err_msg = traceback.format_exc()
        print('err_msg: ', err_msg)
        raise Exception ("Not able to write into dynamodb")        
    print('resp, ', resp)
    
    
    """
    bucket = bucketName 
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
    """
    
    result = {            
        "url_man": "",
        "url_weman": ""
    }
    print('result: ', result)
    
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps(result)
    }
