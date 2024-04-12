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
   
```text   
POST  https://dxt1m1ae24b28.cloudfront.net/photo
{
    "requestId": "b123456abc",
    "bucket": "storage-for-demo-dansing-robot-533267442321-ap-northeast-2",
    "key": "photo/andy_portrait_2.jpg"
}
```

이때의 결과는 아래와 같습니다. 업로드한 파일의 이름에 prefix인 "photo_"를 추가하여 새로운 이름이 생성되었습니다. 생성되는 파일이 여러개일 경우에 "_1", "_2"와 같이 추가됩니다.

```java
{
    "url": "https://dxt1m1ae24b28.cloudfront.net/photo/photo_andy_portrait_2.jpg",
    "time_taken": "19.635620832443237"
}
```

생성된 이미지의 예는 아래와 같습니다.

#### 원본이미지

<img src="https://github.com/kyopark2014/demo-ai-dansing-robot/blob/main/photo-booth/andy_portrait_2.jpg" width="800">

#### 생성된 이미지

생성된 이미지 해상도 조정 및 배경에 대한 최적화 작업은 진행중입니다.

![image](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/ab11c2b3-39c7-431a-bdff-188b1641ef39)


