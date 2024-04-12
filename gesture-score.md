# Gesture에 대한 점수 처리

사용자가 Gesture 수행시에 해당 점수를 Score Dashboard로 전송합니다. 이를 위한 API는 아래와 같습니다.

## Gesture 전달

```java
POST https://dxt1m1ae24b28.cloudfront.net/score_gesture
{
  "userId": "AI-Dancing-Robot-001"
  "requestId": "588c8731-0acf-4127-bf54-841bdc170567",
  "type": "gesture”
  "text": "heart"
}
```
