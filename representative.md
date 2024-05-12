# 대표하는 남여 이미지 생성

데모를 방문하는 사람들의 남/여, 연령등의 정보를 활용하여 대표하는 남여 이미지를 생성합니다.

## 저장 및 활용

저장소의 '/dashboard' 폴더에 "man.png"와 "weman.png"으로 이미지를 생성한 후에, Dashboard에서 활용합니다.

이때 사용되는 방문자 정보는 아래와 같습니다.

1) 성별: 남/여
2) 연령
3) 표정: smile
4) 안경 착용 여부
5) 눈뜨고 있는지 여부
6) 감정: emotion

## 이미지 생성 방법

1) DynamoDB에서 아래와 같은 정보를 추출합니다. 

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
