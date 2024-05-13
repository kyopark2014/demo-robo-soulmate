# Workd Cloud 구현

방문자의 게임 데이터를 통해 로봇과 대화한 내용을 Workd Cloud 형태로 구현하고자 합니다. 이를 위해서는 대화의 내용을 요약하여야 합니다.

## 구현 방안

대화의 내용을 정리후, 게임의 시작/종료시 발생하는 이벤트로 이전 대화의 내용에서 5개의 Topic을 추출합니다. 이후 이를 DyanmoDB에 저장한 후에 QuickSight에서 활용합니다. 관련된 코드는 [workdcloud](./lambda-wordcloud/lambda_function.py) 입니다. 

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


