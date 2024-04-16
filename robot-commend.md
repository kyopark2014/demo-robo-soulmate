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

## 명령어의 처리

[chat.js](./html/chat.js)에 아래와 같이 명령어를 등록합니다.

```java
function initializeCommend() {
    reservedCommend.put('짖어', JSON.stringify({"show": "SAD", "move": "seq", "seq":["LOOK_UP"], "say": "멍! 멍! "}));
    reservedCommend.put('앉아', JSON.stringify({"show": "HAPPY", "move": "seq", "seq":["SIT", "SIT", "SIT", "SIT", "SIT"], "say": "앉았어."}));
    reservedCommend.put('엎드려', JSON.stringify({"show": "HAPPY", "move": "seq", "seq":["SIT", "SIT", "SIT", "SIT", "SIT"], "say": "엎드렸어."}));
    reservedCommend.put('이리 와', JSON.stringify({"show": "HAPPY", "move": "seq", "seq":["MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD", "MOVE_FORWARD"], "say": "그쪽으로 갈게!"}));
    reservedCommend.put('저리가', JSON.stringify({"show": "HAPPY", "move": "seq", "seq":["MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD", "MOVE_BACKWARD"], "say": "멀리 떨어질게!"}));    
}
initializeCommend();
```

### 유사 명령어의 등록

아래와 같이 유사 명령어의 처리를 위하여 '~봐', '~줘'를 포함한 명령어를 추가로 정의합니다.

```java
    reservedCommend.put('짖어', JSON.stringify({"show": "SAD", "move": "seq", "seq":["LOOK_UP"], "say": "멍! 멍! "}));
    reservedCommend.put('짖어봐', JSON.stringify({"show": "SAD", "move": "seq", "seq":["LOOK_UP"], "say": "멍! 멍! "}));
    reservedCommend.put('짖어줘', JSON.stringify({"show": "SAD", "move": "seq", "seq":["LOOK_UP"], "say": "멍! 멍! "}));
```

### 제한된 명령어의 아이디 지정

유사 명령어는 1건으로 count하기 위하여 '이리 와', '이리 와봐', '이리 와줘'로 같은 아이디를 갖도록 합니다.

```java
    limitedCommendId.put('이리 와', 1)
    limitedCommendId.put('이리 와봐', 1)
    limitedCommendId.put('이리 와줘', 1)
```

### 명령어의 수행

아래와 같이 입력이 예약어인 명령어일 경우에 해당되는 동작을 수행합니다.

```java
let counter = new HashMap();
function isReservedCommend(requestId, message){
    console.log('reservedCommend.get('+message+'): '+ reservedCommend.get(message));

    if(reservedCommend.get(message) == undefined) {        
        return false;
    }
    else {
        let commendId = limitedCommendId.get(message);
        console.log('commendId: ', commendId);
        if(commendId == undefined) {
            console.log('commend: ', message);
            sendControl(userId, "commend", "", reservedCommend.get(message), 0, requestId)

            addReceivedMessage(requestId, message+' 동작을 수행합니다.')
        }
        else { 
            let cnt = counter.get(commendId);
            console.log('commend counter: ', cnt);

            if(cnt == undefined || cnt == 0) {
                console.log('commend: ', message);
                sendControl(userId, "commend", "", reservedCommend.get(message), 0, requestId)

                addReceivedMessage(requestId, message+' 동작을 수행합니다.')

                counter.put(commendId, 1);
            }
            else if (cnt>=1) {
                console.log(message+' is only allowed for a time.');

                message = '안돼. 그러지마.';
                console.log('new commend: ', message);
                sendControl(userId, "commend", "", reservedCommend.get(message), 0, requestId)

                addReceivedMessage(requestId, message)
            }
            else {
                console.log('not deifned: '+message+' (cnt='+cnt);
            }
        }
        
        return true;
    }    
}
```

동작 수행 결과는 아래와 같습니다. "엎드려"에 대해 동작을 수행하고, 방문자에게는 "엎드려 동작을 수행합니다."라고 설명하는 메시지를 내보냅니다.

<img width="868" alt="image" src="https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/efc8b631-18f3-4d00-86d5-2ee658253081">

MQTT로 로봇에 전달된 메시지는 아래와 같습니다.

![image](https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/e39579be-88af-4ab9-b70c-291122c8a98e)

제한된 명령어의 경우에 1회만 수행하도록 제한합니다. 게임이 끝나면 제한이 해제됩니다.

<img width="859" alt="image" src="https://github.com/kyopark2014/demo-ai-dansing-robot/assets/52392004/9147835f-b7a4-43fd-a4cc-315b4a3fc060">



