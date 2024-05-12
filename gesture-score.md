# Gesture에 대한 점수 처리

사용자가 Gesture 수행시에 해당 점수를 Score Dashboard로 전송합니다. 이를 위한 API는 아래와 같습니다.

## Gesture 전달

[lambda-score-gesture](./lambda-score-gesture/lambda_function.py)로 '/socre_gesture' API로 gesture를 전달합니다.

```java
POST https://d1r17qhj4m3dnc.cloudfront.net/score_gesture
{
  "userId": "AI-Dancing-Robot-001",
  "requestId": "588c8731-0acf-4127-bf54-841bdc170567",
  "type": "gesture",
  "text": "heart"
}
```

## Gesture Score의 계산식

Guesture의 기본점수 및 항목별 점수는 아래와 같습니다. (To-Do)

## Gesture에 대한 응답

Gesture에 대한 점수 요청시 아래와 같은 응답을 얻습니다.

```java
{
    "isBase64Encoded": false,
    "statusCode": 200,
    "body": "{\"userId\": \"AI-Dancing-Robot-001\", \"requestId\": \"588c8731-0acf-4127-bf54-841bdc170567\", \"score\": 5}"
}
```
