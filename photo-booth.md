# Photo Booth를 위한 생성형 이미지 생성

Photo Booth에서 방문자의 사진을 찍과 얼굴과 배경을 분리하여 새로운 이미지를 생성합니다.

다음과 같은 과정으로 이미지가 생성됩니다.

1) Booth의 Pad올 이용해 사진을 찍고 서버로 전송합니다.
2) Rekognition을 통해 얼굴의 위치(bounding box)를 확인합니다.
3) SageMaker Endpoint로 구성된 SAM을 이용하여 얼굴만 추출합니다.
4) Bedrock의 Titan image generator를 이용해 새로운 이미지를 생성합니다.

## 이미지 업로드 

큰 파일을 보낼수 있도록 presigned url을 이용합니다. 

1) Presigned Url 요청합니다. Client에서 바라보는 CloudFront의 주소는 "dxt1m1ae24b28.cloudfront.net" 입니다. (URL 변경될 수 있습니다) 아래와 같은 방식으로 Presigned url을 요청합니다.

```text
POST https://dxt1m1ae24b28.cloudfront.net/upload
{
  "type": "photo",
  "filename": "andy_portrait_2.jpg",
  "contentType": "image/jpeg"
}
```

이때의 결과는 아래와 같습니다. 여기서 UploadURL은 5분간 유효합니다.

```text
{
    "statusCode": 200,
    "body": "{\"Bucket\":\"storage-for-demo-dansing-robot-533267442321-ap-northeast-2\",\"Key\":\"photo/andy_portrait_2.jpg\",\"Expires\":300,\"ContentType\":\"image/jpeg\",\"UploadURL\":\"https://storage-for-demo-dansing-robot-533267442321-ap-northeast-2.s3.ap-northeast-2.amazonaws.com/docs/andy_portrait_2.jpg?Content-Type=image%2Fjpeg&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIAXYKJXNKIRO3ZJZN4%2F20240410%2Fap-northeast-2%2Fs3%2Faws4_request&X-Amz-Date=20240410T224428Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaDmFwLW5vcnRoZWFzdC0yIkcwRQIhAMv49uyZaGs4FJ3e7NPv3vwVUntkkeVSub3SDKw1eEL4AiA9O%2F6aImNfebK6mxDZvYboSrJ9Ba%2B7BchSqczM0SnNRSqiAwg4EAAaDDUzMzI2NzQ0MjMyMSIMSSHU5cg2k5mSE7KSKv8CeGozybV1giKOi3%2F2SFqUHZuZ%2FwKQgx2SOXkszLUZEUq66ZONMjjjewCn3PiG%2BHFNEc9nqSXVjsPWIb2vRkKG27nwInJF36SibN0qejMI8c9br8KatqHqYAinnduQhrspI3TEJJ0sqF11HZ7odW4eYKZxrofdrod00FeUesSNA%2BI5eCYL7yPEytEViYTeCK%2Fyy7VIS%2FBcGG9bkZhxjgu4gifzUoJm4qll0HjB2prqidtaECI3VcmHHJma13Lhv9ATYo%2BGQtpaxOftl0IJKDEYwRxtxd3pO3%2FlCfqthxbP%2Bx2jHs9lLDiazmekyl4ReU2GJ%2B7bKpFmt2UMRysFjw0aylniq0aEumuH9vnShlzHn5cSLcBCx0K3Dl2DJYR2adPrX2Br4NQUzaNuB9sLqDStYjLNGvy7wwytG6Y3gmfLCXyOttKaTzGP%2F8G&X-Amz-Signature=e8294d3304d4ed60872a4826732777337f1f98a561&X-Amz-SignedHeaders=host\"}"
}
````

2) UploadURL로 HTTP PUT으로 파일을 전송합니다. [chat.js](./html/chat.js)의 "attachFile.addEventListener"를 참조하면 아래와 같습니다. 

```java
var xmlHttp = new XMLHttpRequest();
xmlHttp.open("PUT", uploadURL, true);       
const blob = new Blob([input.files[0]], { type: contentType });
```

3) 이미지 생성을 요청합니다. 이때의 요청하는 URL은 CloudFront의 도메인과 '/photo' API를 이용합니다.

#### Bucket에 업로드되는 파일의 이름으로 이미지들을 생성하는 경우

"id"를 추가하지 않으면 파일명을 기준으로 새로운 이미지들을 생성합니다. 

```text
POST  https://dxt1m1ae24b28.cloudfront.net/photo
{
    "requestId": "a123456abc",
    "bucket": "storage-for-demo-dansing-robot-533267442321-ap-northeast-2",
    "key": "photo/face_image.jpg"
}
```

이때의 결과는 아래와 같습니다.

```java
{
    "url_original": "https://dxt1m1ae24b28.cloudfront.net/photo/face_image.jpg",
    "url_generated": "[\"https://dxt1m1ae24b28.cloudfront.net/photo/photo_face_image_1.jpeg\", \"https://dxt1m1ae24b28.cloudfront.net/photo/photo_face_image_2.jpeg\", \"https://dxt1m1ae24b28.cloudfront.net/photo/photo_face_image_3.jpeg\"]",
    "time_taken": "23.401713371276855"
}
```

#### 포토앱에서 이름을 미리 지정하는 경우

아래와 같이 요청시 "id"를 추가하면 "id"를 기준으로 새로운 이미지들을 생성합니다. 
   
```text   
POST  https://dxt1m1ae24b28.cloudfront.net/photo
{
	"requestId": "a123456abc",
  "bucket": "storage-for-demo-dansing-robot-533267442321-ap-northeast-2",
  "key": "photo/face_image.jpg",
  "id": "507ff273-f8df-11ee-8f9b-69f7819ad4a8"
}
```

이때의 결과는 아래와 같습니다. 업로드한 파일의 이름에 prefix인 "photo_"를 추가하여 새로운 이름이 생성되었습니다. 이때 요청하는 파라메터에 "id"가 있다면, 해당 "id"에 "_1", "_2", "_3"을 붙이고 없다면, uuid로 이름을 붙여 이미지를 생성합니다. 

```java
{
    "url_original": "https://dxt1m1ae24b28.cloudfront.net/photo/face_image.jpg",
    "url_generated": "[\"https://dxt1m1ae24b28.cloudfront.net/photo/photo_507ff273-f8df-11ee-8f9b-69f7819ad4a8_1.jpeg\", \"https://dxt1m1ae24b28.cloudfront.net/photo/photo_507ff273-f8df-11ee-8f9b-69f7819ad4a8_2.jpeg\", \"https://dxt1m1ae24b28.cloudfront.net/photo/photo_507ff273-f8df-11ee-8f9b-69f7819ad4a8_3.jpeg\"]",
    "time_taken": "20.885403871536255"
}
```

이미지에서 얼굴 형상만 추출하기 위하여 Rekognitin으로 face 위치에 대한 box의 위치를 얻은 후에, SAM을 이용하여 아래와 같이 Mask 이미지를 추출합니다. 

```python
def parallel_process_for_SAM(conn, faceInfo, encode_object_image, imgWidth, imgHeight, endpoint_name):  
    box = faceInfo
    left = imgWidth * box['Left']
    top = imgHeight * box['Top']
    
    width = imgWidth * box['Width']
    height = imgHeight * box['Height']
    
    inputs = dict(
        encode_image = encode_object_image,
        input_box = [left, top, left+width, top+height]
    )
    predictions = invoke_endpoint(endpoint_name, inputs)
        
    mask_image = decode_image(json.loads(predictions)['mask_image'])
    
    conn.send(mask_image)
    conn.close()
```


#### 원본이미지

<img src="https://github.com/kyopark2014/demo-ai-dansing-robot/blob/main/photo-booth/andy_portrait_2.jpg" width="800">

#### 생성된 이미지

현재 Titan image generator를 사용할 수 있는 리전이 Virginia와 Oregon이라서 3개의 이미지만 생성하였습니다.


![photo_86db851a-f8dd-11ee-872f-c90482ae9123_1](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/2ee958f9-8292-4147-8cee-5f2a51920850)

![photo_86db851a-f8dd-11ee-872f-c90482ae9123_2](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/c2b3dd10-fb01-47ef-9586-24d581779d21)

![photo_86db851a-f8dd-11ee-872f-c90482ae9123_3](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/770a9d66-b054-49a7-8ff7-aaaea6d1155b)

![photo_86db851a-f8dd-11ee-872f-c90482ae9123_4](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/a0c6e6b3-08d8-493d-a4cc-1e019ffa030a)


## Multiple Faces에 대한 처리

아래와 같이 사진에 여러개의 이미지가 있을 수 있습니다. 그림에 있는 여러 이미지의 마스크를 통합하여 하나의 마스크로 처리합니다.

원본 이미지는 아래와 같습니다. 

![원본](./photo-booth/multiful-faces/5faces_2024_0508_21hr.jpg)

얼굴 이미지 첫번째는 mask로 그대로 활용합니다. 이때, 그림의 (0,0,0)만 True로 처리합니다. 이후 두번째 이미지 부터는 mask와 OR 조건으로 통합합니다. 

```python
isFirst = False
if isFirst == False:
    np_image = np.array(mask_image)
    mask = np.all(np_image == (0, 0, 0), axis = 2)
    isFirst = True
else:
    np_image = np.array(mask_image)
    mask_new = np.all(np_image == (0, 0, 0), axis = 2)
    mask = np.logical_or(mask, mask_new)
```

이후, mask의 값이 True이면 (0,0,0)과 False이면 (255,255,255)로 변환하여 이미지 Mask로 활용합니다. 
```python
for i, row in enumerate(mask):
    for j, value in enumerate(row):
        if value == True:
            np_image[i, j] = (0, 0, 0)
        else:
            np_image[i, j] = (255, 255, 255)
```

통합된 마스크는 아래와 같습니다.

![Mask](./photo-booth/multiful-faces/mask_5faces_2024_0508_21hr.png)

이를 바탕으로 새로 생성한 아미지는 아래와 같습니다. 

![생성된 이미지](./photo-booth/multiful-faces/photo_5faces_2024_0508_21hr_1.jpeg)

## Glasses에 대한 처리

SAM으로 얼굴인식시에 안경에 대한 glasses 처리가 되지 않습니다.

<img src="./photo-booth/glasses/mask_ee9510a5-8049-4ae0-8ec2-6ae043df040d.png" width="500">


이를 Rekognition을 이용해 처리합니다.

```python
def detect_object(target_label, val, imgWidth, imgHeight, np_image):
    Settings = {"GeneralLabels": {"LabelInclusionFilters":[target_label]},"ImageProperties": {"MaxDominantColors":1}}
    
    response = rekognition_client.detect_labels(Image={'Bytes': val},
        MaxLabels=15,
        MinConfidence=0.7,
        # Uncomment to use image properties and filtration settings
        Features=["GENERAL_LABELS", "IMAGE_PROPERTIES"],
        Settings=Settings
    )
    
    box = None
    for item in response['Labels']:
        if len(item['Instances']) > 0:
            for sub_item in item['Instances']:
                box = sub_item['BoundingBox']
                confidence = sub_item['Confidence']
                
                if confidence < 0.7:
                    continue
                
                left = int(imgWidth * box['Left'])
                top = int(imgHeight * box['Top'])
                width = int(imgWidth * box['Width'])
                height = int(imgHeight * box['Height'])

                for i in range(width):
                    for j in range(height):
                        np_image[top+j, left+i] = (0, 0, 0)
    return np_image
```

새로운 Mask 적용 후에 결과는 아래와 같습니다.

![Modified Mask]()

<img src="./photo-booth/glasses/fixed_mask_ee9510a5-8049-4ae0-8ec2-6ae043df040d.png" width="500">

실제 구현된 예는 아래와 같습니다.

- 원본 이미지
<img src="./photo-booth/glasses/faces2024_0502_2202.jpg" width="500">

- 마스크 이미지
<img src="./photo-booth/glasses/mask_faces2024_0502_2202.png" width="500">

- 최종 결과
<img src="./photo-booth/glasses/photo_faces2024_0502_2202_1.jpeg" width="500">

  

  
