# 대표하는 남여 이미지 생성

데모를 방문하는 사람들의 남/여, 연령등의 정보를 활용하여 대표하는 남여 이미지를 생성합니다. 상세한 코드는 [lambda-representative](./lambda-representative/lambda_function.py)을 참조합니다. 

## 저장 및 활용

저장소의 '/dashboard' 폴더에 "man.png"와 "weman.png"으로 이미지를 생성한 후에, Dashboard에서 활용합니다.

이때 사용되는 방문자 정보는 아래와 같습니다.

1) 성별: 남/여
2) 연령
3) 표정: smile
4) 안경 착용 여부
5) 눈뜨고 있는지 여부
6) 감정: emotion

조회되는 데이터 형태는 아래와 같습니다.

```java
{
   "mustache":{
      "BOOL":false
   },
   "generation":{
      "S":"young-adult"
   },
   "beard":{
      "BOOL":false
   },
   "mouthOpen":{
      "BOOL":false
   },
   "time":{
      "S":"2024-05-10 21:15:44"
   },
   "bucket":{
      "S":"storage-for-demo-dansing-robot-533267442321-ap-northeast-2"
   },
   "eyesOpen":{
      "BOOL":true
   },
   "name":{
      "S":"e73da0d5-a333-44f6-a69b-7e0ad5b1e925"
   },
   "gender":{
      "S":"Female"
   },
   "emotions":{
      "S":"CALM"
   },
   "sunglasses":{
      "BOOL":false
   },
   "smile":{
      "BOOL":false
   },
   "id":{
      "S":"e73da0d5-a333-44f6-a69b-7e0ad5b1e925"
   },
   "key":{
      "S":"profile/18ab0cb9-f7bb-44a8-b3ad-c6907c215e50.jpeg"
   },
   "eyeglasses":{
      "BOOL":true
   },
   "age":{
      "N":"23"
   }
}
```

## 이미지 생성 방법

1) DynamoDB에서 방문자 정보를 추출합니다. 

2) 15분 간격으로 아래 Prompt를 이용하여 이미지를 생성합니다.

- Man의 Prompt 예제
```text
The face of a Korean man in his early 30s. A face that smiles 80 percent of the time. No glasses, eyes open, 75 percent of the time. his emotion is mainly Calm. He loves puppy and IT Technology.
```

- Weman의 Prompt 예제

```text  
The face of a Korean woman in her early 30s. A face that smiles 80 percent of the time. No glasses, eyes open, 75 percent of the time. her emotion is mainly Calm. She loves puppy and IT Technology and K-beauty.
```

3) 파일은 항상 동일한 이름으로 overwrite 합니다. 이것은 Dashboad에서 고정 url으로 Dashboard에 접근하기 위함입니다.

## 생성된 이미지

이때 생성된 이미지는 아래와 같습니다.

<img src="./pictures/representative/man.png" width="400">

<img src="./pictures/representative/weman.png" width="400">


## 요청 API

요청은 별도 파라미터없이 '/representative'를 이용합니다. 이 API는 EventBridge를 이용해 15분마다 호출됩니다.

```text
POST https://d1r17qhj4m3dnc.cloudfront.net/representative
```

이때의 결과는 아래와 같습니다. dashboard 이하에 "man.png", "weman.png" 파일을 생성합니다. 기존 파일이 있을 경우에 업데이트 합니다.

```java
{
    "isBase64Encoded": false,
    "statusCode": 200,
    "body": "{\"request_id\": \"0e76a000-10b4-11ef-93ad-63a9feb2230b\", \"generated_urls\": [\"https://d1r17qhj4m3dnc.cloudfront.net/dashboard/man.png\", \"https://d1r17qhj4m3dnc.cloudfront.net/dashboard/weman.png\"]}"
}
```

## 상세 코드

대표하는 이미지에 대한 prompt를 정의합니다. 이때 나이, 감정, smile, eyeopen과 같은 값을 활용합니다. 이후 image generator를 이용해 생성된 이미지에 대한 URL을 생성합니다. 

```python
text_prompt = f"The face of a {age_str}-year-old attractive and handsome korean man. A face that {emotion_str} {smile_str} {glass_str} {eyes_str}. He loves puppy and IT Technology."
    print('text_prompt for man: ', text_prompt)
generated_urls = generatative_image(boto3_bedrock, modelId, k, text_prompt, negative_text, fname, generated_urls)
```

아래와 같이 이미지를 생성합니다.
- cfgScale과 seed를 이용하여 이미지의 생성에 약간에 변화를 줍니다. 방문객의 평균값이 동일하더라도 업데이트 주기마다 약간의 변화를 줌으로써 이미지에 대한 주목도를 높입니다.
- 안경이 없는 경우는 text prompt에 넣지 않고 negativeText에 넣어서 안경이 포함되지 않도록 명시적으로 처리합니다.
- 이미지의 해상도는 dashboard의 해상도와 속도를 고려하여 512x512로 합니다.
- 이미지 생성은 bedrock의 image generator를 이용합니다.
- 이미지는 k개를 생성하여, 방문객이 선호하는 이미지를 선택할 수 있도록 합니다. 

```pytho
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
```        
