import json
import boto3
import os
from urllib import parse
import uuid
import traceback
from botocore.config import Config
import base64
import random

s3_photo_prefix = os.environ.get('s3_photo_prefix')
bucketName = os.environ.get('bucketName')        
path = os.environ.get('path')        
sqsUrl = os.environ.get('sqsUrl')
sqs_client = boto3.client('sqs')
profile_of_Image_LLMs = json.loads(os.environ.get('profile_of_Image_LLMs'))
selected_LLM = 0

tableName = 'EmotionDetailInfo-3d2nq2n4sfcqnfelmjj3n3ycje-dev'

def upload_image_to_s3(object_name,img_b64):
    s3_client = boto3.client('s3')   

    key = 'dashboard/'+object_name
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

def get_random_value():
    return random.randint(1, 30)

def generatative_image(boto3_bedrock, modelId, k, text_prompt, negative_text, fname, generated_urls):    
    cfgScale = 7.5  # default 8, min: 1.1, max: 10.0 (lower value to introduce more randomness)
    seed = 43 + get_random_value()
    print('seed: ', seed)
    
    if negative_text:
        body = json.dumps({
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": text_prompt,      
                "negativeText": negative_text
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
    else:
        body = json.dumps({
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": text_prompt,      
                # "negativeText": negative_text
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
    
    ext = 'png'
    if k==1:
        object_name = fname+'.png'
        
        object_name = f'{fname}.{ext}'        
        url = path+'dashboard'+'/'+parse.quote(object_name)
        print('url: ', url)
        generated_urls.append(url)
            
        img_b64 = response_body["images"][0]
        print(f"Output: {img_b64[0:80]}...")
            
        upload_image_to_s3(object_name,img_b64)
    else:
        for index in range(k):            
            object_name = f'{fname}_{index+1}.{ext}'        
            url = path+'dashboard'+'/'+parse.quote(object_name)
            print('url: ', url)            
            generated_urls.append(url)
            
            img_b64 = response_body["images"][index]
            print(f"Output: {img_b64[0:80]}...")
            
            upload_image_to_s3(object_name,img_b64)

    return generated_urls
            
def lambda_handler(event, context):
    # print('event: ', event)
    
    requestId = str(uuid.uuid1())
    
    emotion = {
        "HAPPY": 0,
        "SURPRISED": 1, 
        "CALM": 2, 
        "ANGRY": 3, 
        "FEAR": 4, 
        "CONFUSED": 5, 
        "DISGUSTED": 6, 
        "SAD": 7
    }
    emotion_counter = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0]
    ]
    
    dynamodb_client = boto3.client('dynamodb')
    try:
        resp = dynamodb_client.scan(
            TableName=tableName
        )
        # print('Items: ', resp["Items"])        
        print('Items[0]: ', resp["Items"][0])
        
        age_sum = [0, 0]
        nglasses = [0, 0]
        nsmile = [0, 0]
        neyesOpen = [0, 0]
        nmouthOpen = [0, 0]
        nbeard = [0, 0]
        nmustache = [0, 0]
        count = [0, 0]
        
        for item in resp["Items"]:
            if item["gender"]["S"] == "Male":
                genderType = 0
            else:
                genderType = 1
            count[genderType] = count[genderType] + 1
            
            print('age: ', item["age"]["N"])    
            print('age_sum[genderType]: ', age_sum[genderType])
            # print('int(age): ', int(item["age"]["N"]))
            
            # age_sum[genderType] = age_sum[genderType] + int(item["age"]["N"])
            ageNum = item["age"]["N"]
            if str.isdigit(item["age"]["N"]):
                ageNum = item["age"]["N"]
            else:
                ageNum = int(item["age"]["N"])
                
            age_sum[genderType] = age_sum[genderType] + ageNum
            
            if item["sunglasses"]["BOOL"] == True or item["eyeglasses"]["BOOL"] == True:
                nglasses[genderType] = nglasses[genderType] + 1
            
            if item["smile"]["BOOL"] == True:
                nsmile[genderType] = nsmile[genderType] + 1
            
            if item["eyesOpen"]["BOOL"] == True:
                neyesOpen[genderType] = neyesOpen[genderType] + 1
            
            if item["mouthOpen"]["BOOL"] == True:
                nmouthOpen[genderType] = nmouthOpen[genderType] + 1
            
            if item["beard"]["BOOL"] == True:
                nbeard[genderType] = nbeard[genderType] + 1
            
            if item["mustache"]["BOOL"] == True:
                nmustache[genderType] = nmustache[genderType] + 1
                
            emotion_counter[genderType][emotion[item["emotions"]["S"]]] = emotion_counter[genderType][emotion[item["emotions"]["S"]]] + 1
                
        avg_age = [30, 25]
        glasses = [True, True]
        smile = [True, True]
        eyesOpen = [True, True]
        mouthOpen = [True, True]
        beard = [True, True]
        mustache = [True, True]
        user_emotion = ["HAPPY", "HAPPY"]
        
        if count[0] > 0:       
            avg_age[0] = age_sum[0] / count[0]            
            glasses[0] = True if nglasses[0] > (count[0]/2) else False
            smile[0] = True if nsmile[0] > (count[0]/2) else False
            
            eyesOpen[0] = True if neyesOpen[0] > (count[0]/2) else False
            mouthOpen[0] = True if nmouthOpen[0] > (count[0]/2) else False
            beard[0] = True if nbeard[0] > (count[0]/2) else False
            mustache[0] = True if nmustache[0] > (count[0]/2) else False

            print('emotion_counter for man: ', emotion_counter[0])            
            maxValue = 0
            pos = 0
            for i, v in enumerate(emotion_counter[0]):
                if v > maxValue:
                    maxValue = v
                    pos = i        
            print('pos for man: ', pos)
            
            if pos == 0:
                user_emotion[0] = 'HAPPY'
            elif pos == 1:
                user_emotion[0] = 'SURPRISED'
            elif pos == 2:
                user_emotion[0] = 'CALM'
            elif pos == 3:
                user_emotion[0] = 'ANGRY'
            elif pos == 4:
                user_emotion[0] = 'FEAR'
            elif pos == 5:
                user_emotion[0] = 'CONFUSED'
            elif pos == 6:
                user_emotion[0] = 'DISGUSTED'
            elif pos == 7:
                user_emotion[0] = 'SAD'
                                
        if count[1] > 0:
            avg_age[1] = age_sum[1] / count[1]
            glasses[1] = True if nglasses[1] > (count[1]/2) else False
            smile[1] = True if nsmile[1] > (count[1]/2) else False
            
            eyesOpen[1] = True if neyesOpen[1] > (count[0]/2) else False
            mouthOpen[1] = True if nmouthOpen[1] > (count[0]/2) else False
            beard[1] = True if nbeard[1] > (count[0]/2) else False
            mustache[1] = True if nmustache[1] > (count[0]/2) else False
            
            print('emotion_counter for weman: ', emotion_counter[1])
            maxValue = 0
            pos = 0
            for i, v in enumerate(emotion_counter[1]):
                if v > maxValue:
                    maxValue = v
                    pos = i        
            print('pos for weman: ', pos)
            
            if pos == 0:
                user_emotion[1] = 'HAPPY'
            elif pos == 1:
                user_emotion[1] = 'SURPRISED'
            elif pos == 2:
                user_emotion[1] = 'CALM'
            elif pos == 3:
                user_emotion[1] = 'ANGRY'
            elif pos == 4:
                user_emotion[1] = 'FEAR'
            elif pos == 5:
                user_emotion[1] = 'CONFUSED'
            elif pos == 6:
                user_emotion[1] = 'DISGUSTED'
            elif pos == 7:
                user_emotion[1] = 'SAD'
        
        print('For man:')    
        print('counter: ', count[0])
        print('avg_age: ', int(avg_age[0]))
        print('glasses: ', glasses[0])
        print('smile: ', smile[0])        
        print('eyesOpen: ', eyesOpen[0])
        print('mouthOpen: ', mouthOpen[0])
        print('beard: ', beard[0])
        print('mustache: ', mustache[0])
        print('emotion: ', user_emotion[0])
            
        print('For weman:')    
        print('avg_age: ', int(avg_age[1]))
        print('counter: ', count[1])
        print('glasses: ', glasses[1])
        print('smile: ', smile[1])
        print('eyesOpen: ', eyesOpen[1])
        print('mouthOpen: ', mouthOpen[1])
        print('beard: ', beard[1])
        print('mustache: ', mustache[1])
        print('emotion: ', user_emotion[1])
                
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
    generated_urls = []
    
    # man    
    age_str = int(avg_age[0])
    smile_str = "smiles," if(smile[0]) == True else ""
    glass_str = "waring glasses," if(glasses[0]) == True else ""    
    negative_text = "glasses," if(glasses[0]) == True else ""
    
    eyes_str = "eyes open" if(eyesOpen[0]) == True else "eyes close"
    emotion_str = user_emotion[0] + ','
    
    #text_prompt = f"The face of a Korean man in his early 30s. A face that smiles 80 percent of the time. No glasses, eyes open, 75 percent of the time. his emotion is mainly Calm. He loves puppy and IT Technology."
    text_prompt = f"The face of a {age_str}-year-old attractive and handsome korean man. A face that {emotion_str} {smile_str} {glass_str} {eyes_str}. He loves puppy and IT Technology."
    print('text_prompt for man: ', text_prompt)
    
    fname = "man"
    generated_urls = generatative_image(boto3_bedrock, modelId, k, text_prompt, negative_text, fname, generated_urls)
         
    # weman
    age_str = int(avg_age[1])
    smile_str = "smiles," if(smile[1]) == True else ""
    glass_str = "waring glasses," if(glasses[1]) == True else ""
    negative_text = "glasses," if(glasses[1]) == True else ""
    
    eyes_str = "eyes open" if(eyesOpen[1]) == True else "eyes close"
    emotion_str = user_emotion[1] + ','
    
    #text_prompt = f"The face of a Korean woman in her early 30s. A face that smiles 80 percent of the time. No glasses, eyes open, 75 percent of the time. her emotion is mainly Calm. She loves puppy and IT Technology and K-beauty."
    text_prompt = f"The face of a {age_str}-year-old attractive and beautiful korean woman. A face that {emotion_str} {smile_str} {glass_str} {eyes_str}. She loves puppy and IT Technology and K-beauty."
    print('text_prompt for weman: ', text_prompt)
    
    fname = "weman"
    generated_urls = generatative_image(boto3_bedrock, modelId, k, text_prompt, negative_text, fname, generated_urls)
    
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
