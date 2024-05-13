# Robo SoulMate 데모

여기에서는 Robo SoulMate 데모를 위한 상세 코드 및 구현 API를 정의합니다. 

전체적인 Architecture는 아래와 같습니다. 
- Voice interpreter와 IoT Controller는 AWS IoT Greengrass에 Component로 설치되고, AI Controller는 로봇의 Chrome 브라우저에 javascript로 구성됩니다.
- 방문자의 음성은 Voice interpreter를 이용하여 텍스트로 변환합합니다. Voice interpreter는 지연시간을 최소화하기 위하여 Amazon Transcribe를 이용하여 음성을 텍스트로 변환합니다.
- 이후 텍스트는 CloudFront - API Gateway - Lambda(redis) - Amazon ElastiCache를 이용해 pubsub 방식으로 AI controller로 전달됩니다.
- 제스처는 Local에서 분석되어 결과가 AI Controller로 전달됩니다.
- 제스처 이외의 이미지 분석은 AI Controller가 Capture한 이미지를 CloudFront - API Gateway - Lambda(gesture)를 거쳐서 Bedrock의 Claude3 (Sonnet)을 이용하여 이미지를 해석합니다.
- 방문객의 음성은 텍스트로 전환되어 Chatbot 형태로 화면에 표시되어 사용자가 AI Robot이 동작하는것을 쉽게 이해할 수 있습니다.
- 변환된 텍스트는 WebSoket 방식으로 API Gateway - Lambda(chat를 통해 Bedrock의 Claud3 (Haiku)를 이용해 처리됩니다. 이때 다양한 사용자의 의도를 Prompt Engineering을 이용해 처리하게 됩니다.
- 최종적으로 결과는 Amazon Polly를 이용해 사용자에게 전달됩니다.
- 이때, Dansing robot은 다양한 동작을 IoT Controller를 이용해 수행합니다.
- 사용자의 접속 및 관련 메트릭은 DynamoDB를 통해 수집되어 QuickSight로 표시됩니다.
- IoT 관련 정보는 IoT SiteWise등을 이용해 별도의 Dashboard에 각종 IoT 정보와 함께 방문객이 확인할 수 있습니다.

![image](./pictures/main-architecture.jpg)

### 로봇에 MBTI 설정하기

대화를 재미있게 하고 게임을 수행하기 위하여 로봇은 8가지의 MBTI를 가질수 있습니다. [mbti.md](./mbti.md)에서 상세한 내용을 확인할 수 있습니다.

### Controller

사용자의 Reaction에 따른 Robot Controler의 동작은 [robot-controller.md](./robot-controller.md)을 참조합니다. 

### Photo Booth

Photo Booth에서는 Stable Diffusion 이미지를 생성합니다. 상세한 내용은 [photo-booth.md](./photo-booth.md)을 참조합니다.

Photo Booth 운영에 필요한 API는 [photo-booth-api.md](./photo-booth-api.md)을 참조합니다. 

### Gesture에 대한 점수

방문자의 Gesture에 대한 응답은 [gesture-score.md](./gesture-score.md)에 따라 처리합니다.

### Robot Command의 수행

미리 예약된 명령어에 대해서는 LLM에 대한 질의없이 바로 해당 명령어를 수행합니다. [robot-command.md](./robot-command.md)에서는 예약어 등록방법에 대해 설명하고 있습니다.


### Game 상태 전달

[game-status.md](./game-status.md)와 같이 Game의 "start", "end"와 같은 이벤트를 모든 client에 전달할 수 있습니다.

### 대표 이미지 생성하기

데모 방문자의 정보를 이용하여 대표 남/여 이미지를 생성합니다. 상세한 내용은 [representative.md](./representative.md)을 참조합니다.

### Word Cloud 구현

방문자들이 사용한 대화이력에서 주요한 토픽을 추출하여 Dashboard에 Word Cloud 형태로 구현합니다. 상세한 내용은 [word-cloud.md](./word-cloud.md)을 참조합니다.

## 데모 준비

### 사전 준비 사항

이 솔루션을 사용하기 위해서는 사전에 아래와 같은 준비가 되어야 합니다.

- [AWS Account 생성](https://repost.aws/ko/knowledge-center/create-and-activate-aws-account)

### 인프라 설치

[인프라 설치](./deployment.md)에 따라 CDK로 인프라 설치를 진행합니다. 

현재는 Interpreter(voice to text)는 terminal에서 직접 명령어를 설치하지만 추후 AWS IoT Greengrass (v2)를 이용하여 component로 자동설치를 수행합니다. 


### 실행결과

## 리소스 정리하기 

더이상 인프라를 사용하지 않는 경우에 아래처럼 모든 리소스를 삭제할 수 있습니다. 

1) [API Gateway Console](https://ap-northeast-2.console.aws.amazon.com/apigateway/main/apis?region=ap-northeast-2)로 접속하여 "rest-api-for-demo-dansing-robot",
"ws-api-for-demo-dansing-robot", "voice-ws-api-for-demo-dansing-robot"을 삭제합니다.

2) [Cloud9 console](https://ap-northeast-2.console.aws.amazon.com/cloud9control/home?region=ap-northeast-2#/)에 접속하여 아래의 명령어로 전체 삭제를 합니다.


```text
cd ~/environment/demo-ai-dansing-robot/cdk-rag-enhanced-searching/ && cdk destroy --all
```
