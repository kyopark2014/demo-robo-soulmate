import boto3
import os
import time
import re
import base64
import boto3
import json

from langchain.prompts import PromptTemplate
from langchain.llms.bedrock import Bedrock
from botocore.config import Config
from PIL import Image
from io import BytesIO
from urllib import parse
import traceback
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_aws import ChatBedrock

bucket = os.environ.get('s3_bucket') # bucket name
s3_prefix = os.environ.get('s3_prefix')
historyTableName = os.environ.get('historyTableName')
speech_prefix = 'speech/'

s3 = boto3.client('s3')
polly = boto3.client('polly')
   
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

    chat = ChatBedrock(   
        model_id=modelId,
        client=boto3_bedrock, 
        model_kwargs=parameters,
    )       
    
    return chat
    
def extract_main_topics(chat, text):
    system = (
        "Summary this conversation in 5 key topics. Put it in <result> tags."
    )
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
        print('translated text: ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")

    return msg[msg.find('<result>')+8:len(msg)-9] # remove <result> tag

    
def lambda_handler(event, context):
    print(event)
    
    start_time = time.time()
    text = event["text"]
        
    # extract main topics in text
    chat = get_chat(profile_of_LLMs, selected_LLM)
    
    topics = extract_main_topics(chat, text)
    print('topics: ', topics)
    
    end_time = time.time()
    time_for_estimation = end_time - start_time
    
    return {
        "isBase64Encoded": False,
        'statusCode': 200,
        'body': json.dumps({            
            "msg": json.dumps(topics),
            "time_taken": str(time_for_estimation)
        })
    }