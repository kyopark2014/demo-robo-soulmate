import json
import boto3
import traceback

client = boto3.client('iot-data')

def lambda_handler(event, context):
    print('event: ', event)
    
    type = event['type']
    print('type: ', type)
    user_id = event['user_id'] # thingName
    print('user_id: ', user_id)
    thingName = user_id
    
    request_id = event['request_id']
    print('request_id: ', request_id)
    
    if type == 'text':
        message = event['message']
        payload = json.dumps({
            "say": message, 
        })
    else:
        score = event['score']
        print('score: ', score)
    
        if score == 5:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        elif score == 4:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        elif score == 3:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        elif score == 2:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        else:
            show = 'HAPPY'
            move = 'seq'
            seq = ["STAND", "SIT"]
        
        payload = json.dumps({
            "show": show,  
            "move": move, 
            "seq": seq
        })
        
    try: 
        response = client.publish(
            topic = f"pupper/do/${thingName}",
            qos = 1,
            payload = payload
        )
        print('response: ', response)        
            
    except Exception:
        err_msg = traceback.format_exc()
        print('error message: ', err_msg)                    
        raise Exception ("Not able to request to LLM")

    return {
        'statusCode': 200,
        'info': json.dumps({
            'result': 'success'
        })
    }
