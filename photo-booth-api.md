# Photo Booth API

여기서는 Photo Booth 운영에 필요한 API를 정의합니다.

## Stand Alone으로 메시지 전송하기

Contrl API를 이용한 메시지 전송하기는 아래와 같습니다.

```text
POST https://dxt1m1ae24b28.cloudfront.net/control
{
  "type": "text",
  "user_id": "AI-Dancing-Robot-007",
  "request_id": "a1234",
  "message": "안녕하세요. 반가워요"
}
```

동작 제어는 아래와 같이 사용합니다. 여기서 commend는 json.dumps()을 이용해 아래와 같은 json 명령어를 사용합니다.

```java
{
   "show":"ANGRY",
   "move":"seq",
   "seq":["TURN_LEFT", "SIT", "TURN_RIGHT"]
}
```

```text
POST  https://dxt1m1ae24b28.cloudfront.net/control
{
  "type": "commend",
  "user_id": "AI-Dancing-Robot-007",
  "request_id": "a1234",
  "commend": "{\n   \"show\":\"ANGRY\",\n   \"move\":\"seq\",\n   \"seq\":[\"TURN_LEFT\", \"SIT\", \"TURN_RIGHT\"]\n}"
}
```

## Welcome 메시지

패드에 있는 포토앱에서 'Start' 버튼 선택하면 Welcome 메시지를 전송합니다. 로봇의 아이디가 "AI-Dancing-Robot-001"인 경우에 아래와 같이 "state"를 "start-photo"로 전송합니다.

```text
POST https://dxt1m1ae24b28.cloudfront.net/redis
{
	"userId": "AI-Dancing-Robot-001",
	"state": "start-photo"
}
```
이때의 결과는 아래와 같습니다. "사진 찍으러 왔구나~ 방문을 환영해! 지금 어떤 기분인지 기념 사진을 남겨보자! 준비 됐지?"와 같은 환영 인사를 합니다.

![image](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/6ed5e455-2d0e-4998-9287-46b156873f12)


## 종료 메시지

패드에 있는 포토앱에서 'End' 버튼 선택하면 종료 메시지를 전송합니다. 이때에 채팅앱은 "잘가! 즐거운 하루 보내!"라고 텍스트와 음성으로 방문자에게 알려줍니다.

```text
HTTP POST https://dxt1m1ae24b28.cloudfront.net/redis
{
	"userId": "AI-Dancing-Robot-001",
	"state": "end-photo"
}
```

## Broadcase 메시지

로봇에게 보내는 메시지를 위한 API를 정의합니다. state를 "broadcast"로 보내면 로봇에 해당 메시지를 출력합니다.

```text
HTTP POST https://dxt1m1ae24b28.cloudfront.net/redis
{
    "userId": "AI-Dancing-Robot-kyoungsu",
    "state": "broadcast", 
    "message": "표정을 보니 오늘 멋진 하루를 보냈나 보네! 나도 기쁘다!"
}
```

## 감정 분석

감정(emotion) 분석용 API는 아래와 같습니다. 

```text
HTTP POST https://dxt1m1ae24b28.cloudfront.net/emotion
바이너리 이미지
```

아래는 Postman의 실행화면입니다. '/emiton' API로 바이너리를 전송합니다. 

<img width="820" alt="image" src="https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/1d311d2e-484c-4790-bbeb-1d3545e4a35c">


이때의 결과는 아래와 같습니다.

```java
{
    "id": "8e02439e-03fd-4d40-afef-49ba4d5470d4",
    "bucket": "storage-for-demo-dansing-robot-533267442321-ap-northeast-2",
    "key": "profile/41435838-75c5-4c9c-a45b-ce6fbaf77548.jpeg",
    "ageRange": {
        "Low": 40,
        "High": 48
    },
    "smile": false,
    "eyeglasses": true,
    "sunglasses": false,
    "gender": "male",
    "beard": false,
    "mustache": false,
    "eyesOpen": true,
    "mouthOpen": false,
    "emotions": "CALM",
    "generation": "adult"
}
```

