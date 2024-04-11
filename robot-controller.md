# Robot Controller

사용자가 로봇과 대화한 텍스트를 Prompt를 이용해 1-5 범위의 Score를 받으면, 로봇은 이에 맞는 Action을 수행합니다. 

## 동작설명

1) Client(javascript)는 API-Gateway의 ‘/control’ API을 통해 REST로 요청합니다.
2) Lambda-control이 MQTT로 Iot Core에 메시지를 전송합니다. 이때, thingName과 client의 ID는 같은 값을 이용하여야 합니다.
3) Request type으로 message와 action을 지정하여 동작을 다르게 합니다.

## Controller 정보

Controller에 전달되는 정보는 아래와 같습니다. 

- user_id: 사용자 아이디, thingName과 같음. 예) AI-Dancing-Robot-000
- request_id: 로깅용
- type: “text” or “action
- message: type이 “text”일때 전달되는 메시지
- score: type이 “action”일때 전달되는 점수


점수를 이용하여 action을 정의는 [관련 코드](./lambda-controller/lambda_function.py)을 참조합니다. 아래의 점수별로 show, move, seq에 대한 정의가 되면 업데이트 하겠습니다.

```python
        score = event['score']
        print('score: ', score)
    
        if score == 5:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        elif score == 4:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        elif score == 3:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        elif score == 2:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        else:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        
        payload = json.dumps({
            "show": show,  
            "move": move, 
            "seq": seq
        })
```

MQTT를 이용해 Robo에 전달되는 값은 아래와 같습니다.

- 사용자가 입력한 메시지는 Robot에서 Polly를 이용해 재생합니다.

- 리엑션 점수에 따라 Robot은 아래와 같은 동작을 수행합니다.
   
![image](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/9f147bc2-069a-4db7-a00a-b8d92cd4aa54)
