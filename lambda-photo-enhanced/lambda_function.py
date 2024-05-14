import boto3
import os
import time
import re
import base64
import boto3
import uuid
import json
import traceback
import copy    
import io
from urllib.parse import unquote_plus
from botocore.config import Config
from PIL import Image
from io import BytesIO
from urllib import parse
from multiprocessing import Process, Pipe
import numpy as np

s3_bucket = os.environ.get('s3_bucket') # bucket name
s3_photo_prefix = os.environ.get('s3_photo_prefix')
sqsUrl = os.environ.get('sqsUrl')
path = os.environ.get('path')

sqs_client = boto3.client('sqs')

list_of_endpoints = [
    "sam-endpoint-2024-04-10-01-35-30",
    "sam-endpoint-2024-04-30-06-08-55"
]
k = 3  # number of generated images 
        
profile_of_Image_LLMs = json.loads(os.environ.get('profile_of_Image_LLMs'))
selected_LLM = 0

seed = 43
cfgScale = 7.5

# random하게 1-30의 사이  
def random_number():
    return np.random.randint(1, 30)

# height = 1152 
# width = 768

smr_client = boto3.client("sagemaker-runtime")
s3_client = boto3.client('s3')   
rekognition_client = boto3.client('rekognition')

secretsmanager = boto3.client('secretsmanager')
def get_secret():
    try:
        get_secret_value_response = secretsmanager.get_secret_value(
            SecretId='bedrock_access_key'
        )
        # print('get_secret_value_response: ', get_secret_value_response)
        secret = json.loads(get_secret_value_response['SecretString'])
        # print('secret: ', secret)
        secret_access_key = json.loads(secret['secret_access_key'])
        access_key_id = json.loads(secret['access_key_id'])
        
        print('length: ', len(access_key_id))
        #for id in access_key_id:
        #    print('id: ', id)
        # print('access_key_id: ', access_key_id)

    except Exception as e:
        raise e
    
    return access_key_id, secret_access_key

access_key_id, secret_access_key = get_secret()
selected_credential = 0
  
def get_client(profile_of_Image_LLMs, selected_LLM, selected_credential):
    print('selected_LLM: ', selected_LLM)
    print('length of profile_of_Image_LLMs: ', len(profile_of_Image_LLMs))
    
    profile = profile_of_Image_LLMs[selected_LLM]
    bedrock_region =  profile['bedrock_region']
    modelId = profile['model_id']
    print(f'LLM: {selected_LLM}, bedrock_region: {bedrock_region}, modelId: {modelId}')
    
    print('access_key_id: ', access_key_id[selected_credential])
    # print('selected_credential: ', selected_credential)
                          
    # bedrock   
    boto3_bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=bedrock_region,
        aws_access_key_id=access_key_id[selected_credential],
        aws_secret_access_key=secret_access_key[selected_credential],
        config=Config(
            retries = {
                'max_attempts': 30
            }            
        )
    )
    
    return boto3_bedrock, modelId

def img_resize(image):
    imgWidth, imgHeight = image.size 
    
    max_length = 1024

    if imgWidth < imgHeight:
        imgWidth = int(max_length/imgHeight*imgWidth)
        imgWidth = imgWidth-imgWidth%64
        imgHeight = max_length
    else:
        imgHeight = int(max_length/imgWidth*imgHeight)
        imgHeight = imgHeight-imgHeight%64
        imgWidth = max_length 

    image = image.resize((imgWidth, imgHeight), resample=0)
    return image

def load_image(bucket, key): 
    image_obj = s3_client.get_object(Bucket=bucket, Key=key)
    image_content = image_obj['Body'].read()
    img = Image.open(BytesIO(image_content))
    
    width, height = img.size 
    print(f"(original) width: {width}, height: {height}, size: {width*height}")
    
    img = img_resize(img)
    
    return img

def image_to_base64(img) -> str:
    """Converts a PIL Image or local image file path to a base64 string"""
    if isinstance(img, str):
        if os.path.isfile(img):
            print(f"Reading image from file: {img}")
            with open(img, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        else:
            raise FileNotFoundError(f"File {img} does not exist")
    elif isinstance(img, Image.Image):
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    else:
        raise ValueError(f"Expected str (filename) or PIL Image. Got {type(img)}")

def decode_image(img):
    img = img.encode("utf8") if type(img) == "bytes" else img    
    # print('encoded image: ', img)
    
    buff = BytesIO(base64.b64decode(img))    
    # print('base64 image: ', base64.b64decode(img))
    
    image = Image.open(buff)
    return image

def invoke_endpoint(endpoint_name, payload):
    response = smr_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Accept="application/json",
        ContentType="application/json",
        Body=json.dumps(payload)
    )
    data = response["Body"].read().decode("utf-8")
    return data

def base64_encode_image(image, formats="PNG"):
    buffer = BytesIO()
    image.save(buffer, format=formats)
    img_str = base64.b64encode(buffer.getvalue())
    return img_str

def generate_outpainting_image(boto3_bedrock, modelId, object_img, mask_img, text_prompt):
    body = json.dumps({
        "taskType": "OUTPAINTING",
        "outPaintingParams": {
            "text": text_prompt,              # Optional
            # "negativeText": negative_prompts,    # Optional
            "image": image_to_base64(object_img),      # Required
            # "maskPrompt": mask_prompt,               # One of "maskImage" or "maskPrompt" is required
            "maskImage": image_to_base64(mask_img),  # Input maskImage based on the values 0 (black) or 255 (white) only
        },                                                 
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "quality": "premium",  # standard, premium,
            # "quality": "standard",
            "cfgScale": cfgScale,
            # "height": height,
            # "width": width,
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
        # print('response: ', response)
        
        # Output processing
        response_body = json.loads(response.get("body").read())
        img_b64 = response_body["images"][0]
        print(f"Output: {img_b64[0:80]}...")
        
        return True, img_b64
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        
        print('current access_key_id: ', access_key_id[selected_credential])
        print('modelId: ', modelId)
        
        profile = profile_of_Image_LLMs[selected_LLM]
        bedrock_region =  profile['bedrock_region']
        print('bedrock_region: ', bedrock_region)
        
        # raise Exception ("Not able to request for bedrock")
        return False, ""         

def parallel_process_for_outpainting(conn, object_img, mask_img, text_prompt, object_name, object_key, selected_LLM, selected_credential):  
    start_time_for_outpainting = time.time()
    
    boto3_bedrock, modelId = get_client(profile_of_Image_LLMs, selected_LLM, selected_credential)
    
    result, img_b64 = generate_outpainting_image(boto3_bedrock, modelId, object_img, mask_img, text_prompt)
    
    if result == True:            
        # upload
        try:
            response = s3_client.put_object(
                Bucket=s3_bucket,
                Key=object_key,
                ContentType='image/jpeg',
                Body=base64.b64decode(img_b64)
            )
            # print('response: ', response)
        except Exception:
                err_msg = traceback.format_exc()
                print('error message: ', err_msg)                
                raise Exception ("Not able to put an object")
        
        print('object_name: ', object_name)    
        url = path+s3_photo_prefix+'/'+parse.quote(object_name)
        print('url: ', url)
            
        end_time_for_outpainting = time.time()
        time_for_outpainting = end_time_for_outpainting - start_time_for_outpainting
        print('time_for_outpainting: ', time_for_outpainting)
    else:
        url = ""
    
    conn.send(url)
    conn.close()

def parallel_process_for_SAM(conn, faceInfo, encode_object_image, imgWidth, imgHeight, endpoint_name):  
    box = faceInfo
    left = imgWidth * box['Left']
    top = imgHeight * box['Top']
    
    print('Left: ' + '{0:.0f}'.format(left))
    print('Top: ' + '{0:.0f}'.format(top))
        
    width = imgWidth * box['Width']
    height = imgHeight * box['Height']
    print('Face Width: ' + "{0:.0f}".format(width))
    print('Face Height: ' + "{0:.0f}".format(height))
    
    inputs = dict(
        encode_image = encode_object_image,
        input_box = [left, top, left+width, top+height]
    )
    predictions = invoke_endpoint(endpoint_name, inputs)
    print('predictions: ', predictions)
        
    mask_image = decode_image(json.loads(predictions)['mask_image'])
    
    conn.send(mask_image)
    conn.close()    

def detect_object(target_label, val, imgWidth, imgHeight, np_image):
    Settings = {"GeneralLabels": {"LabelInclusionFilters":[target_label]},"ImageProperties": {"MaxDominantColors":1}}
    print(f"target_label : {target_label}")
    
    response = rekognition_client.detect_labels(Image={'Bytes': val},
        MaxLabels=15,
        MinConfidence=0.7,
        # Uncomment to use image properties and filtration settings
        Features=["GENERAL_LABELS", "IMAGE_PROPERTIES"],
        Settings=Settings
    )
    print('rekognition response: ', response)
    
    box = None
    for item in response['Labels']:
        # print(item)
        if len(item['Instances']) > 0:
            print(item)
            print(item['Name'], item['Confidence'])

            for sub_item in item['Instances']:
                box = sub_item['BoundingBox']
                confidence = sub_item['Confidence']
                
                if confidence < 0.7:
                    continue
                
                left = int(imgWidth * box['Left'])
                top = int(imgHeight * box['Top'])
                width = int(imgWidth * box['Width'])
                height = int(imgHeight * box['Height'])

                print(f"imgWidth : {imgWidth}, imgHeight : {imgHeight}")
                print(f"Left: {left}")
                print(f"Top: {top}")          
                print(f"Object Width: {width}")
                print(f"Object Height: {height}")
                
                for i in range(width):
                    for j in range(height):
                        np_image[top+j, left+i] = (0, 0, 0)

    return np_image
                    
def lambda_handler(event, context):
    global selected_credential, selected_LLM
        
    print(event)
    

    outpaint_prompt =[ 
        "a whimsical and enchanting background featuring a magnificent unicorn. Depicting the mythical creature standing in a lush, verdant meadow surrounded by vibrant wildflowers and towering, twisting willow trees. Incorporate ethereal elements like glittering streams, rainbow-hued butterflies, and beams of warm sunlight filtering through the canopy. Imbuing the scene with a sense of magic and wonder",
    #    "a background image of  a powerful robotic character with devil-like features, posing heroically amid explosive action effects. Surrounding the robot are other characters. The composition is energetic, with exaggerated proportions, bold outlines, and a striking color palette dominated by bright primaries.",
        "A highly detailed digital background image of a futuristic city on a floating island, with towering skyscrapers made of sleek chrome and glass, hovering above the clouds against a vibrant sunset sky filled with shades of orange, pink, and purple.",
        "a breathtaking cosmic landscape, filled with swirling galaxies, nebulae, and stars. Creating a mesmerizing interplay of vibrant colors, from deep indigos and violets to fiery oranges and reds. Incorporating intricate details and a sense of depth, making the viewer feel like they're floating amidst the wonders of the universe."
    #    "a breathtaking, surreal background image that combines elements of nature and fantasy. a lush, vibrant forest with towering trees and mystical creatures. Incorporating intricate details like glowing mushrooms, ancient ruins, and a shimmering waterfall cascading into a crystal-clear pond. Let your imagination run wild, and infusing the scene with a sense of wonder and enchantment.",    
    #    "A futuristic cityscape , focusing purely on the architecture and technology. The scene shows a skyline dominated by towering skyscrapers", 
    #    "A medieval village with thatched-roof cottages, villagers in period clothing, and a bustling market square during a festival",   
    #    "A panoramic view of a futuristic city by the sea, with a serene waterfront, advanced aquatic transport systems, and shimmering buildings reflecting the setting sun."
    #    'A festive scene in a future city during a high-tech festival, with streets filled with people in colorful smart fabrics, interactive digital art installations, and joyous music.'
    ] 
      
    
    for record in event['Records']:
        receiptHandle = record['receiptHandle']
        print("receiptHandle: ", receiptHandle)
        
        body = record['body']
        print("body: ", body)
        
        jsonBody = json.loads(body)        
        bucket = jsonBody['bucket']       # bucket
        print('request body: ', json.dumps(jsonBody))
         
        # translate to utf8
        key = unquote_plus(jsonBody['key']) # key
        print('bucket: ', bucket)
        print('key: ', key)        
            
        start_time_for_photo_generation= time.time()
        
        requestId = jsonBody["requestId"]  # request id
        print('requestId: ', requestId)

        # url
        url_original = path+parse.quote(key)
        print('url_original: ', url_original)
        
        # filenmae
        if "id" in jsonBody:
            id = jsonBody["id"]
        else:
            # id = uuid.uuid1()
            finename = key.split('/')[-1]
            print('finename: ', finename)
            id = finename.split('.')[0]
        print('id: ', id)
        
        # ext
        ext = key.split('.')[-1]
        if ext == 'jpg':
            ext = 'jpeg'
        
        # load image
        img = load_image(bucket, key) # load image from bucket    
        object_image = copy.deepcopy(img)
        encode_object_image = base64_encode_image(object_image,formats=ext.upper()).decode("utf-8")

        # detect faces
        buffer = BytesIO()
        img.save(buffer, format='jpeg', quality=100)
        val = buffer.getvalue()

        response = rekognition_client.detect_faces(Image={'Bytes': val},Attributes=['ALL'])
        print('rekognition response: ', response)
        print('number of faces: ', len(response['FaceDetails']))
        
        imgWidth, imgHeight = img.size           

        start_time_for_detection = time.time()
        
        # Earn mask image for multiple faces
        processes = []
        parent_connections = []
        selected_endpoint = 0
        
        print(f"imgWidth : {imgWidth}, imgHeight : {imgHeight}")
        isFirst = False
        for faceDetail in response['FaceDetails']:
            print('The detected face is between ' + str(faceDetail['AgeRange']['Low']) 
                + ' and ' + str(faceDetail['AgeRange']['High']) + ' years old')

            parent_conn, child_conn = Pipe()
            parent_connections.append(parent_conn)
            
            print('selected_endpoint: ', selected_endpoint)
            endpoint_name = list_of_endpoints[selected_endpoint] 
            print('endpoint_name: ', endpoint_name)
            
            process = Process(target=parallel_process_for_SAM, args=(child_conn, faceDetail['BoundingBox'], encode_object_image, imgWidth, imgHeight, endpoint_name))
            processes.append(process)
            
            selected_endpoint = selected_endpoint + 1
            if selected_endpoint >= len(list_of_endpoints):
                selected_endpoint = 0
                
        for process in processes:
            process.start()
                        
        for parent_conn in parent_connections:
            mask_image = parent_conn.recv()
            
            print('merge current mask')      
            if isFirst==False:       
                np_image = np.array(mask_image)
                #print('np_image: ', np_image)
                mask = np.all(np_image == (0, 0, 0), axis=2)
                
                isFirst = True
            else: 
                np_image = np.array(mask_image)            
                mask_new = np.all(np_image == (0, 0, 0), axis=2)
                
                mask = np.logical_or(mask, mask_new)
        
        for process in processes:
            process.join()

        # update mask        
        print('mask: ', mask)
        for i, row in enumerate(mask):
            for j, value in enumerate(row):
                if value == True:
                    np_image[i, j] = (0, 0, 0)
                else:
                    np_image[i, j] = (255, 255, 255)
            
        # detect glasses and sunglasses
        target_label = 'Glasses'
        np_image= detect_object(target_label, val, imgWidth, imgHeight, np_image)
        
        target_label = 'Sunglasses'
        np_image= detect_object(target_label, val, imgWidth, imgHeight, np_image)                
        # print('np_image: ', np_image)
        
        # generate mask image
        merged_mask_image = Image.fromarray(np_image)
                
        # upload mask image for debugging
        pixels = BytesIO()
        merged_mask_image.save(pixels, "png")
        
        fname = 'mask_'+key.split('/')[-1].split('.')[0]    
        pixels.seek(0, 0)
        response = s3_client.put_object(
            Bucket=s3_bucket,
            Key='photo/'+fname+'.png',
            ContentType='image/png',
            Body=pixels
        )
        #print('response: ', response)
            
        end_time_for_detection = time.time()
        time_for_detection = end_time_for_detection - start_time_for_detection
        print('time_for_detection: ', time_for_detection)
        
        # generate outpainting image
        object_img = img_resize(object_image)
        mask_img = img_resize(merged_mask_image)
            
        print('start outpainting.....')      
        generated_urls = []    
        processes = []       
        parent_connections = []         
        for i in range(k):
            parent_conn, child_conn = Pipe()
            parent_connections.append(parent_conn)
                                
            # text_prompt =  f'a human with a {outpaint_prompt[i]} background'
            text_prompt = f'a neatly and well-dressed human with yellow cute robot dog in {outpaint_prompt[i]}'
                    
            object_name = f'photo_{id}_{i+1}.{ext}'
            object_key = f'{s3_photo_prefix}/{object_name}'  
            print('generated object_key: ', object_key)
                
            process = Process(target=parallel_process_for_outpainting, args=(child_conn, object_img, mask_img, text_prompt, object_name, object_key, selected_LLM, selected_credential))
            processes.append(process)
            
            selected_LLM = selected_LLM + 1
            if selected_LLM >= len(profile_of_Image_LLMs):
                selected_LLM = 0
        
        for process in processes:
            process.start()
                        
        for parent_conn in parent_connections:
            url = parent_conn.recv()
            
            if url:
                generated_urls.append(url)
            else:
                print('url is empty')

        for process in processes:
            process.join()
        
        print('completed outpainting.....')      
        end_time_for_photo_generation= time.time()
        time_for_photo_generation = end_time_for_photo_generation - start_time_for_photo_generation
        print('time_for_photo_generation: ', time_for_photo_generation)
                
        print('generated_urls: ', json.dumps(generated_urls))
        
        # fre debugging
        print('len(access_key): ', len(access_key_id))
        print('current access_key_id: ', access_key_id[selected_credential])
        #print('selected_credential: ', selected_credential)
        
        if selected_credential >= len(access_key_id)-1:
            selected_credential = 0
        else:
            selected_credential = selected_credential + 1
            
        result = {            
            "url_original": url_original,
            "url_generated": json.dumps(generated_urls),
            "time_taken": str(time_for_photo_generation)
        }
        print('result: ', result)

    # delete queue
    try:
        sqs_client.delete_message(QueueUrl=sqsUrl, ReceiptHandle=receiptHandle)
        print('delete queue message: ', sqsUrl)
    except Exception as e:        
        print('Fail to delete the queue message: ', e)
        
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps(result)
    }
