# Game의 상태 알림

여기에서는 Game의 시작, 종료와 같은 event를 로봇들에 전달하는 API에 대해 설명합니다.

게임 시작을 전달하는 event는 아래와 같습니다.

```java
POST  https://dxt1m1ae24b28.cloudfront.net/redis
{
	"userId": "all",
	"state": "start"
}
```

게임 종료를 알리는 event는 아래와 같습니다.

```java
POST  https://dxt1m1ae24b28.cloudfront.net/redis
{
	"userId": "all",
  	"state": "end"
}
```

## 동작 설명

[lambda-redis](./lambda-redis/lambda_function.py)에서는 데모에 사용하는 리스트를 아래와 같이 가지고 있습니다. '/redis'를 통해 state가 "start", "end"와 같이 전달이 되면, "type"을 "game"로 지정하고 state를 포함한 JSON message를 Redis로 Publish 합니다. 결과적으로 리스트에 있는 모든 client에게 game의 state가 전달됩니다.



```python
def push_game_event(state):
    list = {
        "AI-Dancing-Robot-000",
        "AI-Dancing-Robot-001",
        "AI-Dancing-Robot-002",
        "AI-Dancing-Robot-003",
        "AI-Dancing-Robot-004",
        "AI-Dancing-Robot-005",
        "AI-Dancing-Robot-006",
        "AI-Dancing-Robot-007",
        "AI-Dancing-Robot-008",
        "AI-Dancing-Robot-kyoungsu",        
    }
    
    for userId in list:    
        msg = {
            "type": "game",
            "userId": userId,
            "requestId": str(uuid.uuid4()),
            "query": "",
            "state": state
        }
        
        channel = f"{userId}"   
        try: 
            redis_client.publish(channel=channel, message=json.dumps(msg))
            print('successfully published: ', json.dumps(msg))
        
        except Exception:
            err_msg = traceback.format_exc()
            print('error message: ', err_msg)                    
            raise Exception ("Not able to request")
```
