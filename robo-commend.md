# Robot Commend

여기서는 Rule 방식의 Robot Commend에 대해 정의합니다. LLM을 거치지 않고 예약된 명령어에 따라 로봇이 동작하게 하면, 지연시간을 최소화하면서 원하는 명령어를 수행할 수 있습니다.

## Commend Definition

룰베이스 커맨드 예시 (~봐, ~줘, 로 끝나는 내용 동일)

- 짖어
```java
{"show": "SAD", "move": "seq", "seq":["LOOK_UP"], "say": "멍! 멍! "}
```

- 앉아
```java
{"show": "HAPPY", "move": "seq", "seq":["SIT", "SIT", "SIT", "SIT", "SIT"], "say": "앉았어."}
```

- 엎드려

```java
{"show": "HAPPY", "move": "seq", "seq":["SIT", "SIT", "SIT", "SIT", "SIT"], "say": "엎드렸어."}
```

- 이리 와 (게임 당 횟수 제한 1회)

```java
{"show": "HAPPY", "move": "seq", "seq":["MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD"], "say": "그쪽으로 갈게!"}
```

- 저리가 (게임 당 횟수 제한 1회)

```java
{"show": "HAPPY", "move": "seq", "seq":["MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD"], "say": "멀리 떨어질게!"}
```


- 횟수 제한 있는 명령어는 한번 실행한 후 아래 명령어로 통일

```java
{"show": "SAD", "move": "seq", "seq":["LOOK_LEFT","LOOK_RIGHT", "LOOK_LEFT", "LOOK_RIGHT" ], "say": "안돼. 그러지마."}
```
