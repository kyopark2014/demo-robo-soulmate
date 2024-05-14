import boto3
import os
import time
import datetime
import boto3
import json
import traceback
import uuid

from langchain.prompts import PromptTemplate
from botocore.config import Config
from pytz import timezone
    
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_aws import ChatBedrock

tableName = os.environ.get('tableName') 
profile_of_LLMs = json.loads(os.environ.get('profile_of_LLMs'))
selected_LLM = 0
   
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"

def get_chat(profile_of_LLMs, selected_LLM):
    profile = profile_of_LLMs[selected_LLM]
    bedrock_region =  profile['bedrock_region']
    modelId = profile['model_id']
    print(f'LLM: {selected_LLM}, bedrock_region: {bedrock_region}, modelId: {modelId}')
    maxOutputTokens = int(profile['maxOutputTokens'])
                          
    # bedrock   
    boto3_bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=bedrock_region,
        config=Config(
            retries = {
                'max_attempts': 30
            }            
        )
    )
    parameters = {
        "max_tokens":maxOutputTokens,     
        "temperature":0.1,
        "top_k":250,
        "top_p":0.9,
        "stop_sequences": [HUMAN_PROMPT]
    }
    # print('parameters: ', parameters)

    chat = ChatBedrock(   
        model_id=modelId,
        client=boto3_bedrock, 
        model_kwargs=parameters,
    )       
    
    return chat
    
def extract_main_topics(chat, text):
    system = (
        #"Summary this conversation in 5 key topics. 5개 토픽을 자바스크립트 리스트에 담아서 보관해줘. Put it in <result> tags."
"""<history> tag안에는 Human과 AI의 대화가 있습니다. 여기에서 5가지 topic울 추출하세요. 결과는 <example>과 같이 list로 정리하세요. 또한, 결과는 <result> tag를 붙여주세요. 
<example>        
["좋아하는 음식", "인사와 소개", "여행", "취미 및 관심사", "재미있는 놀이"]
</example>        
""")
    human = "<history>{text}</history>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text,
            }
        )
        msg = result.content
        print('msg: ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")

    return msg[msg.find('<result>')+8:len(msg)-9] # remove <result> tag
    
def lambda_handler(event, context):
    print(event)        
    start_time = time.time()    
    
    text = event["text"]
    print('text: ', text)
    userId = event["userId"]
    print('userId: ', userId)
        
    # extract main topics in text
    chat = get_chat(profile_of_LLMs, selected_LLM)    
    topics = json.loads(extract_main_topics(chat, text)) 
    print('topics: ', topics)
    
    requestId = str(uuid.uuid4())
    timestamp = str(time.time())
    print('requestId: ', requestId)
    print('timestamp: ', timestamp)
    
    timestr = datetime.datetime.now(timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
    print('timestr: ', timestr)
            
    dynamo_client = boto3.client('dynamodb')
    for i, topic in enumerate(topics):
        print('topic: ', topic)
        
        id = f"{requestId}_{i}"
        item = {
            'userId': {'S':userId},
            'requestId': {'S':id},
            'timestamp': {'S':timestr},
            'topic': {'S':topic}
        }
        
        try:
            resp =  dynamo_client.put_item(TableName=tableName, Item=item)
            print('resp: ', resp)
        except Exception:
            err_msg = traceback.format_exc()
            print('error message: ', err_msg)
            raise Exception ("Not able to write into dynamodb")               
        
    end_time = time.time()
    time_for_estimation = end_time - start_time
    print('time_for_estimation: ', time_for_estimation)
    
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps({            
            "msg": json.dumps(topics),
            "time_taken": str(time_for_estimation)
        })
    }