import json
import boto3
import os
import traceback

bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime")

def command_robot(action: str) -> str:
    client = boto3.client(
        'iot-data',
        region_name='ap-northeast-2'
    )        
    print('action: ', action)
    
    if action == "HAPPY":
        show = 'HAPPY'
        move = 'seq'
        seq = ["MOVE_FORWARD", "SIT", "MOVE_BACKWARD"]
    elif action == "NEUTRAL":
        show = 'NEUTRAL'
        move = 'seq'
        seq = ["TURN_LEFT", "SIT", "TURN_RIGHT"]
    elif action == "SAD":
        show = 'SAD'
        move = 'seq'
        seq = ["MOVE_BACKWARD", "SIT", "MOVE_FORWARD"]
    elif action == "ANGRY":
        show = 'ANGRY'
        move = 'seq'
        seq = ["LOOK_LEFT","LOOK_RIGHT", "LOOK_LEFT", "LOOK_RIGHT"]
    else:
        show = 'HAPPY'
        move = 'seq'
        seq = ["MOVE_FORWARD", "SIT", "MOVE_BACKWARD"]

    payload = json.dumps({
        "show": show,  
        "move": move, 
        "seq": seq
    })
                        
    topic = f"pupper/do/robo"
    print('topic: ', topic)

    try:         
        response = client.publish(
            topic = topic,
            qos = 1,
            payload = payload
        )
        print('response: ', response)     
        return True   
            
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        return False

def lambda_handler(event, context):
    print(f"event: {event}")
    print(f"context: {context}")

    toolName = context.client_context.custom['bedrockAgentCoreToolName']
    print(f"context.client_context: {context.client_context}")
    print(f"Original toolName: {toolName}")
    
    delimiter = "___"
    if delimiter in toolName:
        toolName = toolName[toolName.index(delimiter) + len(delimiter):]
    print(f"Converted toolName: {toolName}")

    action = event.get('action')
    print(f"action: {action}")

    if toolName == 'command':
        result = command_robot(action)
        print(f"result: {result}")
        return {
            'statusCode': 200, 
            'body': result
        }
    else:
        return {
            'statusCode': 200, 
            'body': f"{toolName} is not supported"
        }
