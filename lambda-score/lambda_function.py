import boto3
import os
import time
import boto3
import json

from botocore.config import Config
import traceback
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import BedrockChat

HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"

selected_LLM = 0
profile_of_LLMs = json.loads(os.environ.get('profile_of_LLMs'))

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

    chat = BedrockChat(
        model_id=modelId,
        client=boto3_bedrock, 
        streaming=True,
        callbacks=[StreamingStdOutCallbackHandler()],
        model_kwargs=parameters,
    )        
    
    return chat

def extract_sentiment(chat, text):
    system = (
        """What is the sentiment of the following review. The result should be one of "positive", "negative", or "neural". Put it in <result> tags."""
    )
        
    human = "<review>{text}</review>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    # print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )        
        msg = result.content                
        # print('result of sentiment extraction: ', msg)
        
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return msg[msg.find('<result>')+8:len(msg)-9] # remove <result> tag
    
def lambda_handler(event, context):
    print(event)    
    
    userId = event["userId"]         
    requestId = event["requestId"]
    text = event["text"]     
    print('text: ', text)
    
    start_time_for_greeting = time.time()
        
    # creating greeting message
    chat = get_chat(profile_of_LLMs, selected_LLM)    

    result = extract_sentiment(chat, text)
    print('result: ', result)
    
    end_time_for_greeting = time.time()
    time_for_greeting = end_time_for_greeting - start_time_for_greeting
    
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps({         
            "userId": userId,
            "requestId": requestId,
            "result": result,
            "time_taken": str(time_for_greeting)
        })
    }