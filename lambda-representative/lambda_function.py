import json
import boto3
import os
from urllib import parse
import uuid
import traceback
from botocore.config import Config
import base64

s3_photo_prefix = os.environ.get('s3_photo_prefix')
bucketName = os.environ.get('bucketName')        
path = os.environ.get('path')        
sqsUrl = os.environ.get('sqsUrl')
sqs_client = boto3.client('sqs')
profile_of_Image_LLMs = json.loads(os.environ.get('profile_of_Image_LLMs'))
selected_LLM = 0

tableName = 'EmotionDetailInfo-3d2nq2n4sfcqnfelmjj3n3ycje-dev'

def generatative_image(boto3_bedrock, modelId, k, text_prompt, fname):    
    cfgScale = 7.5  # default 8, min: 1.1, max: 10.0 (lower value to introduce more randomness)
    seed = 43
    body = json.dumps({
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": text_prompt,      
            # "negativeText": "string"
        },
        "imageGenerationConfig": {
            "numberOfImages": k,
            "quality": "premium", # standard, premium
            "height": 512,
            "width": 512,
            "cfgScale": cfgScale,
            "seed": seed
        }
    })
    
    try: 
        response = boto3_bedrock.invoke_model(
            body=body,
            modelId=modelId,
            accept="application/json", 
            contentType="application/json"
        )
        print('image generation response: ', response)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request for bedrock")
                
    # Output processing
    response_body = json.loads(response.get("body").read())
    img_b64 = response_body["images"][0]
    print(f"Output: {img_b64[0:80]}...")
    
    # upload
    s3_client = boto3.client('s3')   

    ext = "png"
    key = f"dashboard/{fname}.{ext}"
    try:
        response = s3_client.put_object(
            Bucket=bucketName,
            Key=key,
            ContentType='image/png',
            Body=base64.b64decode(img_b64)
        )
        # print('response: ', response)
    except Exception:
            err_msg = traceback.format_exc()
            print('error message: ', err_msg)                
            raise Exception ("Not able to put an object")

def lambda_handler(event, context):
    print('event: ', event)
    
    requestId = event["requestId"]
    print('requestId: ', requestId)

    dynamodb_client = boto3.client('dynamodb')
    try:
        resp = dynamodb_client.scan(
            TableName=tableName
        )
        print('Items: ', resp["Items"])
        
        print('Items[0]: ', resp["Items"][0])
        
        
    except Exception as ex:
        err_msg = traceback.format_exc()
        print('err_msg: ', err_msg)
        raise Exception ("Not able to write into dynamodb")        
    print('resp, ', resp)
    
    # bedrock       
    profile = profile_of_Image_LLMs[selected_LLM]
    bedrock_region =  profile['bedrock_region']
    
    boto3_bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=bedrock_region,
        config=Config(
            retries = {
                'max_attempts': 30
            }            
        )
    )
    
    k = 1
    modelId = profile['model_id']
    text_prompt = "The face of a Korean man in his early 30s. A face that smiles 80 percent of the time. No glasses, eyes open, 75 percent of the time. his emotion is mainly Calm. He loves puppy and IT Technology."
    gender = 'man'
    if gender == "man":
        fname = "man"
    else:
        fname = "woman"
    generatative_image(boto3_bedrock, modelId, k, text_prompt, fname)
            
    generated_urls = []    
    ext = 'png'
    for index in range(k):
        object_name = f'photo_{fname}_{index+1}.{ext}'
    
        url = path+'dashboard'+'/'+parse.quote(object_name)
        print('url: ', url)
        
        generated_urls.append(url)
    
    result = {      
        "request_id": requestId,
        "generated_urls": generated_urls
    }
    print('result: ', result)
    
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps(result)
    }
