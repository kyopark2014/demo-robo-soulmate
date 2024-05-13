# Word Cloud 구현

방문자의 게임 데이터를 통해 로봇과 대화한 내용을 Workd Cloud 형태로 구현하고자 합니다. 이를 위해서는 대화의 내용을 요약하여야 합니다.

## 구현 방안

대화의 내용을 정리후, 게임의 시작/종료시 발생하는 이벤트로 이전 대화의 내용에서 5개의 Topic을 추출합니다. 이후 이를 DyanmoDB에 저장한 후에 QuickSight에서 활용합니다. 상세한 코드는 [workdcloud](./lambda-wordcloud/lambda_function.py)에서 확인할 수 있습니다. 

대화의 내용을 요약할 때는 아래와 같이 JSON 형태로 결과를 요청한 후에 <result></result> 태그내용을 추출해서 사용합니다.

```python
def extract_main_topics(chat, text):
    system = (
        #"Summary this conversation in 5 key topics. 5개 토픽을 자바스크립트 리스트에 담아서 보관해줘. Put it in <result> tags."
        "다음의 대화를 5가지 topic으로 정리해줘. 이때 결과를 자바스크립트 리스트에 담아서 보관해줘. 또한 결과는 <result> tag를 붙여주세요."
    )
    human = "<history>{text}</history>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text,
            }
        )
        msg = result.content
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")

    return msg[msg.find('<result>')+8:len(msg)-9] # remove <result> tag
```

extract_main_topics()을 이용하여 아래와 같이 주제어(topic)을 추출한 후에 DynamoDB에 저장합니다. 이때, 중복을 방지하기 위하여 Partition key로 userIdㅇ와 requestId를 이용합니다. 

```python
    # extract main topics in text
    chat = get_chat(profile_of_LLMs, selected_LLM)    
    topics = json.loads(extract_main_topics(chat, text)) 
    print('topics: ', topics)
    
    requestId = str(uuid.uuid4())
    timestamp = str(time.time())
    print('requestId: ', requestId)
    print('timestamp: ', timestamp)
    
    dynamo_client = boto3.client('dynamodb')
    for i, topic in enumerate(topics):
        print('topic: ', topic)
        
        id = f"{requestId}_{i}"
        item = {
            'userId': {'S':userId},
            'requestId': {'S':id},
            'timestamp': {'S':timestamp},
            'topic': {'S':topic}
        }
        
        try:
            resp =  dynamo_client.put_item(TableName=tableName, Item=item)
            print('resp: ', resp)
        except Exception:
            err_msg = traceback.format_exc()
            print('error message: ', err_msg)
            raise Exception ("Not able to write into dynamodb")      
```

대화내용은 [lambda-chat](./lambda-chat-ws/lambda_function.py)에서 아래와 같이 수집후 전송합니다.

대화가 종료할때 요청과 응답을 dialog에 "Human:"과 "AI:"를 Prefix로 붙여서 저장합니다. 

```python
dialog = dialog + f"Human: {text}\n"
dialog = dialog + f"AI: {msg}\n"
```

이후 아래와 같이 대화내용을 lambda로 전송하여 Topic 추출 및 DynamoDB에 저장작업을 수행합니다.

```python
if len(dialog)>10:
    function_name = "lambda-wordcloud-for-demo-dansing-robot"
    lambda_region = 'ap-northeast-2'
    try:

        lambda_client = get_lambda_client(region=lambda_region)
        payload = {
             "userId": userId,
             "text": dialog
         }
         response = lambda_client.invoke(
             FunctionName=function_name,
             Payload=json.dumps(payload),
         )
    
         dialog = ""
     except Exception:
         err_msg = traceback.format_exc()
         print('error message: ', err_msg)
```

### 퍼미션

Lambda Invoke를 위한 퍼미션은 아래와 같습니다. invokeLambdaPolicy로 policy를 생성하여 활용합니다.

```java
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Invoke",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": "*"
        }
    ]
}
```
