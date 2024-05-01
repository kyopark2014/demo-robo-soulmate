# Photo Booth API

여기서는 Photo Booth 운영에 필요한 API를 정의합니다.

## Welcome 메시지

패드에 있는 포토앱에서 'Start' 버튼 선택시에 대한 이벤트 전송방법입니다. 로봇의 아이디가 "AI-Dancing-Robot-001"인 경우에 아래와 같이 "state"를 "start-photo"로 전송합니다.

```text
HTTP POST https://dxt1m1ae24b28.cloudfront.net/redis
{
	"userId": "AI-Dancing-Robot-001",
	"state": "start-photo"
}
```
이때의 결과는 아래와 같습니다. "사진 찍으러 왔구나~ 방문을 환영해! 지금 어떤 기분인지 기념 사진을 남겨보자! 준비 됐지?"와 같은 환영 인사를 합니다.

![image](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/6ed5e455-2d0e-4998-9287-46b156873f12)
