import json
import boto3
import os
import time
import datetime
import PyPDF2
import csv
import sys
import re
import traceback
import base64

import uuid
from botocore.config import Config
from io import BytesIO
from urllib import parse
from PIL import Image
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import BedrockChat
from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain_core.messages import HumanMessage, SystemMessage
from multiprocessing import Process, Pipe

s3 = boto3.client('s3')
s3_bucket = os.environ.get('s3_bucket') # bucket name
s3_prefix = os.environ.get('s3_prefix')
callLogTableName = os.environ.get('callLogTableName')
bedrock_region = os.environ.get('bedrock_region', 'us-west-2')
path = os.environ.get('path')
doc_prefix = s3_prefix+'/'
    
profile_of_LLMs = json.loads(os.environ.get('profile_of_LLMs'))
selected_LLM = 0

intents = [
    {
        "id": "dansing",
        "action": "춤을 춰주세요.",
        "message": "[Action] 네 멋진 춤을 출테니 기쁘게 봐주세요."        
    },
    {
        "id": "quiz",
        "action": "퀴즈 풀어주세요",
        "message": "[Action] 네 그러면 재미있는 문제를 낼테니 잘 맞춰보세요."
    },
    {
        "id": "game-feeding",
        "action": "간석 먹고 싶어?",
        "message": "[Action] 주인님 최고! 제가 좋아하는 간식 아시나요?"
    },
    {
        "id": "gesture",
        "action": "제스처 게임하고 싶어",
        "message": "[Action] 이제 제스처 게임을 하겠습니다. 카메라를 보며 하트를 한번 해보세요."
    },
    {
        "id": "greeting",
        "action": "인사해봐",
        "message": "[Action] 사진에서 고객님의 기분을 파악하여 적절한 인사말을 합니다."
    },
    {
        "id": "reading",
        "action": "다음을 읽어줘",
        "message": "[Action] 사진 속의 문장을 텍스트로 읽어옵니다."
    },
    {
        "id": "translation",
        "action": "번역해줘",
        "message": "[Action] 사진의 문장을 한국어로 번역합니다."
    },
    {
        "id": "stop_action",
        "action": "그만",
        "message": "[Action] Action을 멈추고 다시 일반적인 대화를 시작합니다."
    }
]
   
# websocket
connection_url = os.environ.get('connection_url')
client = boto3.client('apigatewaymanagementapi', endpoint_url=connection_url)
print('connection_url: ', connection_url)

HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"

# Multi-LLM
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

def get_embedding(profile_of_LLMs, selected_LLM):
    profile = profile_of_LLMs[selected_LLM]
    bedrock_region =  profile['bedrock_region']
    modelId = profile['model_id']
    print(f'Embedding: {selected_LLM}, bedrock_region: {bedrock_region}, modelId: {modelId}')
    
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
    
    bedrock_embedding = BedrockEmbeddings(
        client=boto3_bedrock,
        region_name = bedrock_region,
        model_id = 'amazon.titan-embed-text-v1' 
    )  
    
    return bedrock_embedding

map_chain = dict() 
action_dict = dict()
MSG_LENGTH = 100

# load documents from s3 for pdf and txt
def load_document(file_type, s3_file_name):
    s3r = boto3.resource("s3")
    doc = s3r.Object(s3_bucket, s3_prefix+'/'+s3_file_name)
    
    if file_type == 'pdf':
        contents = doc.get()['Body'].read()
        reader = PyPDF2.PdfReader(BytesIO(contents))
        
        raw_text = []
        for page in reader.pages:
            raw_text.append(page.extract_text())
        contents = '\n'.join(raw_text)    
        
    elif file_type == 'txt':        
        contents = doc.get()['Body'].read().decode('utf-8')
        
    print('contents: ', contents)
    new_contents = str(contents).replace("\n"," ") 
    print('length: ', len(new_contents))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " ", ""],
        length_function = len,
    ) 

    texts = text_splitter.split_text(new_contents) 
    print('texts[0]: ', texts[0])
    
    return texts

# load csv documents from s3
def load_csv_document(s3_file_name):
    s3r = boto3.resource("s3")
    doc = s3r.Object(s3_bucket, s3_prefix+'/'+s3_file_name)

    lines = doc.get()['Body'].read().decode('utf-8').split('\n')   # read csv per line
    print('lins: ', len(lines))
        
    columns = lines[0].split(',')  # get columns
    #columns = ["Category", "Information"]  
    #columns_to_metadata = ["type","Source"]
    print('columns: ', columns)
    
    docs = []
    n = 0
    for row in csv.DictReader(lines, delimiter=',',quotechar='"'):
        # print('row: ', row)
        #to_metadata = {col: row[col] for col in columns_to_metadata if col in row}
        values = {k: row[k] for k in columns if k in row}
        content = "\n".join(f"{k.strip()}: {v.strip()}" for k, v in values.items())
        doc = Document(
            page_content=content,
            metadata={
                'name': s3_file_name,
                'row': n+1,
            }
            #metadata=to_metadata
        )
        docs.append(doc)
        n = n+1
    print('docs[0]: ', docs[0])

    return docs

def get_summary(chat, docs):    
    text = ""
    for doc in docs:
        text = text + doc
    
    if isKorean(text)==True:
        system = (
            "다음의 <article> tag안의 문장을 요약해서 500자 이내로 설명하세오."
        )
    else: 
        system = (
            "Here is pieces of article, contained in <article> tags. Write a concise summary within 500 characters."
        )
    
    human = "<article>{text}</article>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )
        
        summary = result.content
        print('result of summarization: ', summary)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return summary
    
def load_chatHistory(userId, allowTime, chat_memory):
    dynamodb_client = boto3.client('dynamodb')

    response = dynamodb_client.query(
        TableName=callLogTableName,
        KeyConditionExpression='user_id = :userId AND request_time > :allowTime',
        ExpressionAttributeValues={
            ':userId': {'S': userId},
            ':allowTime': {'S': allowTime}
        }
    )
    print('query result: ', response['Items'])

    for item in response['Items']:
        text = item['body']['S']
        msg = item['msg']['S']
        type = item['type']['S']

        if type == 'text':
            print('text: ', text)
            print('msg: ', msg)        

            chat_memory.save_context({"input": text}, {"output": msg})             

def getAllowTime():
    d = datetime.datetime.now() - datetime.timedelta(days = 2)
    timeStr = str(d)[0:19]
    print('allow time: ',timeStr)

    return timeStr

def isKorean(text):
    # check korean
    pattern_hangul = re.compile('[\u3131-\u3163\uac00-\ud7a3]+')
    word_kor = pattern_hangul.search(str(text))
    # print('word_kor: ', word_kor)

    if word_kor and word_kor != 'None':
        print('Korean: ', word_kor)
        return True
    else:
        print('Not Korean: ', word_kor)
        return False

def general_conversation(chat, query):
    global time_for_inference, history_length, token_counter_history    
    time_for_inference = history_length = token_counter_history = 0
    
    if isKorean(query)==True :
        system = (
            "다음의 Human과 Assistant의 친근한 이전 대화입니다. Assistant은 상황에 맞는 구체적인 세부 정보를 충분히 제공합니다. Assistant의 이름은 서연이고, 모르는 질문을 받으면 솔직히 모른다고 말합니다."
        )
    else: 
        system = (
            "Using the following conversation, answer friendly for the newest question. If you don't know the answer, just say that you don't know, don't try to make up an answer. You will be acting as a thoughtful advisor."
        )
    
    human = "{input}"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), MessagesPlaceholder(variable_name="history"), ("human", human)])
    print('prompt: ', prompt)
    
    history = memory_chain.load_memory_variables({})["chat_history"]
    print('memory_chain: ', history)
                
    chain = prompt | chat    
    try: 
        isTyping()  
        stream = chain.invoke(
            {
                "history": history,
                "input": query,
            }
        )
        msg = readStreamMsg(stream.content)    
                            
        msg = stream.content
        print('msg: ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)        
            
        sendErrorMessage(err_msg)    
        raise Exception ("Not able to request to LLM")
    
    return msg

def isTyping():    
    msg_proceeding = {
        'request_id': requestId,
        'msg': 'Proceeding...',
        'status': 'istyping'
    }
    #print('result: ', json.dumps(result))
    sendMessage(msg_proceeding)
        
def readStreamMsg(stream):
    msg = ""
    if stream:
        for event in stream:
            # print('event: ', event)
            # msg = msg + event

            result = {
                'request_id': requestId,
                'msg': event,
                'status': 'proceeding'
            }
            #print('result: ', json.dumps(result))
            sendMessage(result)
    # print('msg: ', msg)
    return msg
    
def sendMessage(body):
    try:
        client.post_to_connection(
            ConnectionId=connectionId, 
            Data=json.dumps(body)
        )
    except Exception:
        err_msg = traceback.format_exc()
        print('err_msg: ', err_msg)
        raise Exception ("Not able to send a message")
    
def deliveryVoiceMessage(action, msg):    
    requestId = uuid.uuid4()
    print('requestId: ', requestId)
    result = {
        'request_id': str(requestId),
        'action': action,
        'msg': msg,
        'status': 'redirected'
    }
    #print('debug: ', json.dumps(debugMsg))
    sendMessage(result)      

def sendResultMessage(action, msg):    
    result = {
        'request_id': requestId,
        'action': action,
        'msg': msg,
        'status': 'completed'
    }
    #print('debug: ', json.dumps(debugMsg))
    sendMessage(result)
        
def sendErrorMessage(msg):
    errorMsg = {
        'request_id': requestId,
        'msg': msg,
        'status': 'error'
    }
    print('error: ', json.dumps(errorMsg))
    sendMessage(errorMsg)    

def load_chat_history(userId, allowTime):
    dynamodb_client = boto3.client('dynamodb')
    print('loading history.')

    try: 
        response = dynamodb_client.query(
            TableName=callLogTableName,
            KeyConditionExpression='user_id = :userId AND request_time > :allowTime',
            ExpressionAttributeValues={
                ':userId': {'S': userId},
                ':allowTime': {'S': allowTime}
            }
        )
        print('query result: ', response['Items'])
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to DynamoDB")

    for item in response['Items']:
        text = item['body']['S']
        msg = item['msg']['S']
        type = item['type']['S']

        if type == 'text':
            memory_chain.chat_memory.add_user_message(text)
            if len(msg) > MSG_LENGTH:
                memory_chain.chat_memory.add_ai_message(msg[:MSG_LENGTH])                          
            else:
                memory_chain.chat_memory.add_ai_message(msg)     

def translate_text(chat, text):
    system = (
        "You are a helpful assistant that translates {input_language} to {output_language} in <article> tags. Put it in <result> tags."
    )
    human = "<article>{text}</article>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    if isKorean(text)==False :
        input_language = "English"
        output_language = "Korean"
    else:
        input_language = "Korean"
        output_language = "English"
                        
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "input_language": input_language,
                "output_language": output_language,
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

def check_grammer(chat, text):
    if isKorean(text)==True:
        system = (
            "다음의 <article> tag안의 문장의 오류를 찾아서 설명하고, 오류가 수정된 문장을 답변 마지막에 추가하여 주세요."
        )
    else: 
        system = (
            "Here is pieces of article, contained in <article> tags. Find the error in the sentence and explain it, and add the corrected sentence at the end of your answer."
        )
        
    human = "<article>{text}</article>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )
        
        msg = result.content
        print('result of grammer correction: ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return msg

def extract_sentiment(chat, text):
    if isKorean(text)==True:
        system = (
            """아래의 <example> review와 Extracted Topic and sentiment 인 <result>가 있습니다.
            <example>
            객실은 작지만 깨끗하고 편안합니다. 프론트 데스크는 정말 분주했고 체크인 줄도 길었지만, 직원들은 프로페셔널하고 매우 유쾌하게 각 사람을 응대했습니다. 우리는 다시 거기에 머물것입니다.
            </example>
            <result>
            청소: 긍정적, 
            서비스: 긍정적
            </result>

            아래의 <review>에 대해서 위의 <result> 예시처럼 Extracted Topic and sentiment 을 만들어 주세요."""
        )
    else: 
        system = (
            """Here is <example> review and extracted topics and sentiments as <result>.

            <example>
            The room was small but clean and comfortable. The front desk was really busy and the check-in line was long, but the staff were professional and very pleasant with each person they helped. We will stay there again.
            </example>

            <result>
            Cleanliness: Positive, 
            Service: Positive
            </result>"""
        )
        
    human = "<review>{text}</review>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )        
        msg = result.content                
        print('result of sentiment extraction: ', msg)
        
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return msg

def extract_information(chat, text):
    if isKorean(text)==True:
        system = (
            """다음 텍스트에서 이메일 주소를 정확하게 복사하여 한 줄에 하나씩 적어주세요. 입력 텍스트에 정확하게 쓰여있는 이메일 주소만 적어주세요. 텍스트에 이메일 주소가 없다면, "N/A"라고 적어주세요. 또한 결과는 <result> tag를 붙여주세요."""
        )
    else: 
        system = (
            """Please precisely copy any email addresses from the following text and then write them, one per line.  Only write an email address if it's precisely spelled out in the input text. If there are no email addresses in the text, write "N/A".  Do not say anything else.  Put it in <result> tags."""
        )
        
    human = "<text>{text}</text>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )        
        output = result.content        
        msg = output[output.find('<result>')+8:len(output)-9] # remove <result> 
        
        print('result of information extraction: ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return msg

def remove_pii(chat, text):
    if isKorean(text)==True:
        system = (
            """아래의 <text>에서 개인식별정보(PII)를 모두 제거하여 외부 계약자와 안전하게 공유할 수 있도록 합니다. 이름, 전화번호, 주소, 이메일을 XXX로 대체합니다. 또한 결과는 <result> tag를 붙여주세요."""
        )
    else: 
        system = (
            """We want to de-identify some text by removing all personally identifiable information from this text so that it can be shared safely with external contractors.
            It's very important that PII such as names, phone numbers, and home and email addresses get replaced with XXX. Put it in <result> tags."""
        )
        
    human = "<text>{text}</text>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )        
        output = result.content        
        msg = output[output.find('<result>')+8:len(output)-9] # remove <result> 
        
        print('result of removing PII : ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return msg

def do_step_by_step(chat, text):
    if isKorean(text)==True:
        system = (
            """다음은 Human과 Assistant의 친근한 대화입니다. Assistant은 상황에 맞는 구체적인 세부 정보를 충분히 제공합니다. 아래 문맥(context)을 참조했음에도 답을 알 수 없다면, 솔직히 모른다고 말합니다. 여기서 Assistant의 이름은 서연입니다.

            Assistant: 단계별로 생각할까요?

            Human: 예, 그렇게하세요."""
        )
    else: 
        system = (
            """Using the following conversation, answer friendly for the newest question. If you don't know the answer, just say that you don't know, don't try to make up an answer. You will be acting as a thoughtful advisor. 
            
            Assistant: Can I think step by step?

            Human: Yes, please do."""
        )
        
    human = "<text>{text}</text>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )        
        msg = result.content        
        
        print('result of sentiment extraction: ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return msg

def extract_timestamp(chat, text):
    system = (
        """Human: 아래의 <text>는 시간을 포함한 텍스트입니다. 친절한 AI Assistant로서 시간을 추출하여 아래를 참조하여 <example>과 같이 정리해주세요.
            
        - 년도를 추출해서 <year>/<year>로 넣을것 
        - 월을 추출해서 <month>/<month>로 넣을것
        - 일을 추출해서 <day>/<day>로 넣을것
        - 시간을 추출해서 24H으로 정리해서 <hour>/<hour>에 넣을것
        - 분을 추출해서 <minute>/<minute>로 넣을것

        이때의 예제는 아래와 같습니다.
        <example>
        2022년 11월 3일 18시 26분
        </example>
        <result>
            <year>2022</year>
            <month>11</month>
            <day>03</day>
            <hour>18</hour>
            <minute>26</minute>
        </result>

        결과에 개행문자인 "\n"과 글자 수와 같은 부가정보는 절대 포함하지 마세요."""
    )    
        
    human = "<text>{text}</text>"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "text": text
            }
        )        
        output = result.content        
        msg = output[output.find('<result>')+8:len(output)-9] # remove <result> 
        
        print('result of sentiment extraction: ', msg)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return msg

def search_intent_using_prompt_engineering(chat, intents, query):
    context = ""
    for i, intent in enumerate(intents):
        idx = i+1
        context += f"{idx}. {intent['action']}\n"
    print('context: ', context)
    
    system = (
        """다음의 <context> tag의 예제에서 질문과 가장 가까운 항목을 선택해 주세요.
            
        <context>
        {context}
        </context>

        질문과 관련있는 항목이 없으면 None이라고 답변합니다. <result> tag를 붙여주세요."""
    )    
        
    human = "{input}"
    
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    print('prompt: ', prompt)
    
    chain = prompt | chat    
    try: 
        result = chain.invoke(
            {
                "context": context,
                "input": query
            }
        )        
        output = result.content        
        output_without_tag = output[output.find('<result>')+8:len(output)-9] # remove <result> 
        
        action = output_without_tag[output_without_tag.find('.')+2:]
        print('action: ', action)
        
        for intent in intents:
            if intent['action'] == action:
                print('result of intent search: ', json.dumps(intent))
                return True, intent
        
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return False, {}

def search_intent_using_similarity_search(intents, query):
    global vectorstore
        
    embedding = get_embedding(profile_of_LLMs, selected_LLM)
    for intent in intents:
        doc = []
        doc.append(
            Document(
                page_content=intent['action'],
                metadata={
                    'id': intent['id'],
                    'message': intent['message'],
                }
            )
        ) 

        vectorstore = FAISS.from_documents(
            doc,  # documents
            embedding  # embeddings            
        )
        
    top_k = 3
    rel_documents = vectorstore.similarity_search_with_score(
        query=query,
        k=top_k        
    )
        
    for i, document in enumerate(rel_documents):
        print(f'## Document(intent search) {i+1}: {document}')

        id = document[0].metadata['id']
        message = document[0].metadata['message']
        action = document[0].page_content
        print(f"similarity search: {id}: {message}: {action}")

def use_multimodal(chat, img_base64, query):    
    if query == "":
        query = "그림에 대해 상세히 설명해줘."
    
    messages = [
        SystemMessage(content="답변은 500자 이내의 한국어로 설명해주세요."),
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}", 
                    },
                },
                {
                    "type": "text", "text": query
                },
            ]
        )
    ]
    
    try: 
        result = chat.invoke(messages)
        
        summary = result.content
        print('result of code summarization: ', summary)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return summary

def earn_gesture(chat, img_base64, query):    
    if query == "":
        query = "그림에서 사람이 표현하는 Guesture에 대해 설명해줘."
    
    messages = [
        SystemMessage(content="답변은 500자 이내의 한국어로 설명해주세요."),
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}", 
                    },
                },
                {
                    "type": "text", "text": query
                },
            ]
        )
    ]
    
    try: 
        result = chat.invoke(messages)
        
        summary = result.content
        print('result of code summarization: ', summary)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return summary

def extract_text(chat, img_base64):    
    query = "텍스트를 추출해서 utf8로 변환하세요. <result> tag를 붙여주세요."
    
    messages = [
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}", 
                    },
                },
                {
                    "type": "text", "text": query
                },
            ]
        )
    ]
    
    try: 
        result = chat.invoke(messages)
        
        extracted_text = result.content
        print('result of text extraction from an image: ', extracted_text)
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")
    
    return extracted_text
        
def getResponse(jsonBody):
    print('jsonBody: ', jsonBody)
    
    userId  = jsonBody['user_id']
    print('userId: ', userId)
    requestId  = jsonBody['request_id']
    print('requestId: ', requestId)
    requestTime  = jsonBody['request_time']
    print('requestTime: ', requestTime)
    type  = jsonBody['type']
    print('type: ', type)
    body = jsonBody['body']
    print('body: ', body)
    convType = jsonBody['convType']
    print('convType: ', convType)
            
    global map_chain, memory_chain, selected_LLM
    
    # Multi-LLM
    profile = profile_of_LLMs[selected_LLM]
    bedrock_region =  profile['bedrock_region']
    modelId = profile['model_id']
    print(f'selected_LLM: {selected_LLM}, bedrock_region: {bedrock_region}, modelId: {modelId}')
    # print('profile: ', profile)
    
    chat = get_chat(profile_of_LLMs, selected_LLM)    
    # bedrock_embedding = get_embedding(profile_of_LLMs, selected_LLM)
    
    # create memory
    if userId in map_chain:  
        print('memory exist. reuse it!')        
        memory_chain = map_chain[userId]        
    else: 
        print('memory does not exist. create new one!')        
        memory_chain = ConversationBufferWindowMemory(memory_key="chat_history", output_key='answer', return_messages=True, k=10)
        map_chain[userId] = memory_chain

        allowTime = getAllowTime()
        load_chat_history(userId, allowTime)
        print('history was loaded')
                
    # load action
    if userId in action_dict:
        print("Action: ", action_dict[userId])
    else:
        print('There is no action that was previously defined.')
        action_dict[userId] = 'general'
    
    start = int(time.time())    

    msg = ""
    if type == 'text' and body[:11] == 'list models':
        bedrock_client = boto3.client(
            service_name='bedrock',
            region_name=bedrock_region,
        )
        modelInfo = bedrock_client.list_foundation_models()    
        print('models: ', modelInfo)

        msg = f"The list of models: \n"
        lists = modelInfo['modelSummaries']
        
        for model in lists:
            msg += f"{model['modelId']}\n"
        
        msg += f"current model: {modelId}"
        print('model lists: ', msg)    
    else:             
        if type == 'text':
            text = body
            print('query: ', text)

            querySize = len(text)
            textCount = len(text.split())
            print(f"query size: {querySize}, words: {textCount}")
            
            # Intent Search
            # LLM search
            # similarity search
            search_intent_using_similarity_search(intents, text)
            
            isAction, intent = search_intent_using_prompt_engineering(chat, intents, text)
            if isAction:
                msg = intent['message']
                print('Intent message: ', msg)
                
                if intent['id'] == 'stop_action':
                    action_dict[userId] = 'general'
                else:
                    action_dict[userId] = intent['id']
                    
                print('current intent: ', action_dict[userId])
                
            else:
                if text == 'clearMemory':
                    memory_chain.clear()
                    map_chain[userId] = memory_chain
                        
                    print('initiate the chat memory!')
                    msg  = "The chat memory was intialized in this session."
                else:            
                    if convType == "normal":
                        msg = general_conversation(chat, text)    
                    elif convType == "translation":
                        msg = translate_text(chat, text) 
                    elif convType == "grammar":
                        msg = check_grammer(chat, text)  
                    elif convType == "sentiment":
                        msg = extract_sentiment(chat, text)
                    elif convType == "extraction": # infomation extraction
                        msg = extract_information(chat, text)  
                    elif convType == "pii":
                        msg = remove_pii(chat, text)   
                    elif convType == "step-by-step":
                        msg = do_step_by_step(chat, text)  
                    elif convType == "timestamp-extraction":
                        msg = extract_timestamp(chat, text)  
                    else:
                        msg = general_conversation(chat, text)  
                        
            memory_chain.chat_memory.add_user_message(text)
            memory_chain.chat_memory.add_ai_message(msg)
                    
        elif type == 'document':
            isTyping()
            
            object = body
            file_type = object[object.rfind('.')+1:len(object)]            
            print('file_type: ', file_type)
            
            if file_type == 'csv':
                docs = load_csv_document(path, doc_prefix, object)
                contexts = []
                for doc in docs:
                    contexts.append(doc.page_content)
                print('contexts: ', contexts)

                msg = get_summary(chat, contexts)
                        
            elif file_type == 'pdf' or file_type == 'txt' or file_type == 'md' or file_type == 'pptx' or file_type == 'docx':
                texts = load_document(file_type, object)

                docs = []
                for i in range(len(texts)):
                    docs.append(
                        Document(
                            page_content=texts[i],
                            metadata={
                                'name': object,
                                # 'page':i+1,
                                'uri': path+doc_prefix+parse.quote(object)
                            }
                        )
                    )
                print('docs[0]: ', docs[0])    
                print('docs size: ', len(docs))

                contexts = []
                for doc in docs:
                    contexts.append(doc.page_content)
                print('contexts: ', contexts)

                msg = get_summary(chat, contexts)
            
            elif file_type == 'png' or file_type == 'jpeg' or file_type == 'jpg':
                print('multimodal: ', object)
                
                s3_client = boto3.client('s3') 
                    
                image_obj = s3_client.get_object(Bucket=s3_bucket, Key=s3_prefix+'/'+object)
                # print('image_obj: ', image_obj)
                
                image_content = image_obj['Body'].read()
                img = Image.open(BytesIO(image_content))
                
                width, height = img.size 
                print(f"width: {width}, height: {height}, size: {width*height}")
                
                isResized = False
                while(width*height > 5242880):                    
                    width = int(width/2)
                    height = int(height/2)
                    isResized = True
                    print(f"width: {width}, height: {height}, size: {width*height}")
                
                if isResized:
                    print(f'The image will be resized with ({width} / {height})')
                    img = img.resize((width, height))
                    print(f'The image was resized with ({width} / {height})')
                
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                if 'commend' in jsonBody:
                    commend  = jsonBody['commend']
                else:
                    commend = ""
                print('commend: ', commend)
                
                # verify the image
                msg = use_multimodal(chat, img_base64, commend)       
                
                # extract text from the image
                text = extract_text(chat, img_base64)
                extracted_text = text[text.find('<result>')+8:len(text)-9] # remove <result> tag
                print('extracted_text: ', extracted_text)
                if len(extracted_text)>10:
                    msg = msg + f"\n\n[추출된 Text]\n{extracted_text}\n"
                
                memory_chain.chat_memory.add_user_message(f"{object}에서 텍스트를 추출하세요.")
                memory_chain.chat_memory.add_ai_message(extracted_text)
                
        elapsed_time = int(time.time()) - start
        print("total run time(sec): ", elapsed_time)
        
        print('msg: ', msg)

        item = {
            'user_id': {'S':userId},
            'request_id': {'S':requestId},
            'request_time': {'S':requestTime},
            'type': {'S':type},
            'body': {'S':body},
            'msg': {'S':msg}
        }

        client = boto3.client('dynamodb')
        try:
            resp =  client.put_item(TableName=callLogTableName, Item=item)
        except Exception:
            err_msg = traceback.format_exc()
            print('error message: ', err_msg)
            raise Exception ("Not able to write into dynamodb")               
        #print('resp, ', resp)

    if selected_LLM >= len(profile_of_LLMs)-1:
        selected_LLM = 0
    else:
        selected_LLM = selected_LLM + 1
    
    sendResultMessage(action_dict[userId], msg)  
    
    return msg

def lambda_handler(event, context):
    # print('event: ', event)    
    global connectionId, requestId
    
    msg = ""
    if event['requestContext']: 
        connectionId = event['requestContext']['connectionId']        
        routeKey = event['requestContext']['routeKey']
        
        if routeKey == '$connect':
            print('connected!')
        elif routeKey == '$disconnect':
            print('disconnected!')
        else:
            body = event.get("body", "")
            #print("data[0:8]: ", body[0:8])
            if body[0:8] == "__ping__":
                # print("keep alive!")                
                sendMessage("__pong__")
            else:
                print('connectionId: ', connectionId)
                print('routeKey: ', routeKey)
        
                jsonBody = json.loads(body)
                print('request body: ', json.dumps(jsonBody))

                requestId  = jsonBody['request_id']
                try:                    
                    msg = getResponse(jsonBody)
                    print('msg: ', msg)
                    
                except Exception:
                    err_msg = traceback.format_exc()
                    print('err_msg: ', err_msg)

                    sendErrorMessage(err_msg)    
                    raise Exception ("Not able to send a message")

    return {
        'statusCode': 200
    }