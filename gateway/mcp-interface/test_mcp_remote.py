import asyncio
import os
import json
import boto3
import requests

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import logging
import sys

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("test_mcp_remote")


def load_config():
    config = None
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)    
    return config

config = load_config()

projectName = config['projectName']
region = config['region']

def create_cognito_bearer_token(config):
    """Get a fresh bearer token from Cognito"""
    try:
        cognito_config = config['cognito']
        client_id = cognito_config['client_id']
        username = cognito_config['test_username']
        password = cognito_config['test_password']
        
        # Create Cognito client
        client = boto3.client('cognito-idp', region_name=region)
        
        # Authenticate and get tokens
        response = client.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        auth_result = response['AuthenticationResult']
        access_token = auth_result['AccessToken']
        # id_token = auth_result['IdToken']
        
        print("Successfully obtained fresh Cognito tokens")
        return access_token
        
    except Exception as e:
        print(f"Error getting Cognito token: {e}")
        return None

def get_bearer_token():
    try:
        secret_name = config['secret_name']
        session = boto3.Session()
        client = session.client('secretsmanager', region_name=region)
        response = client.get_secret_value(SecretId=secret_name)
        bearer_token_raw = response['SecretString']
        
        token_data = json.loads(bearer_token_raw)        
        if 'bearer_token' in token_data:
            bearer_token = token_data['bearer_token']
            return bearer_token
        else:
            print("No bearer token found in secret manager")
            return None
    
    except Exception as e:
        print(f"Error getting stored token: {e}")
        return None

def save_bearer_token(secret_name, bearer_token):
    try:        
        session = boto3.Session()
        client = session.client('secretsmanager', region_name=region)
        
        # Create secret value with bearer_key 
        secret_value = {
            "bearer_key": "mcp_server_bearer_token",
            "bearer_token": bearer_token
        }
        
        # Convert to JSON string
        secret_string = json.dumps(secret_value)
        
        # Check if secret already exists
        try:
            client.describe_secret(SecretId=secret_name)
            # Secret exists, update it
            client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_string
            )
            print(f"Bearer token updated in secret manager with key: {secret_value['bearer_key']}")
        except client.exceptions.ResourceNotFoundException:
            # Secret doesn't exist, create it
            client.create_secret(
                Name=secret_name,
                SecretString=secret_string,
                Description="MCP Server Cognito credentials with bearer key and token"
            )
            print(f"Bearer token created in secret manager with key: {secret_value['bearer_key']}")
            
    except Exception as e:
        print(f"Error saving bearer token: {e}")
        # Continue execution even if saving fails

async def main():
    # Check basic AWS connectivity
    bearer_token = get_bearer_token()
    print(f"Bearer token from secret manager: {bearer_token if bearer_token else 'None'}")
    #print(f"Bearer token from secret manager: {bearer_token}")

    if not bearer_token:    
        # Try to get fresh bearer token from Cognito
        print("No bearer token found in secret manager, getting fresh bearer token from Cognito...")
        bearer_token = create_cognito_bearer_token(config)
        print(f"Bearer token from cognito: {bearer_token if bearer_token else 'None'}")
        
        if bearer_token:
            secret_name = config['secret_name']
            save_bearer_token(secret_name, bearer_token)
        else:
            print("Failed to get bearer token from Cognito. Exiting.")
            return
                    
    mcp_url = config['gateway_url']
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    print(f"MCP URL: {mcp_url}")
    print(f"Headers: {headers}")

    # Prepare the request body for MCP initialization
    request_body = json.dumps({
        "jsonrpc": "2.0",
        "id": "1",
        "method": "initialize", 
        "params": {
            "protocolVersion": "2024-11-05", 
            "capabilities": {}, 
            "clientInfo": {
                "name": "test-client", 
                "version": "1.0.0"
            }
        }
    })
    
    successful_url = None
    successful_headers = None
    
    # url test
    try:
        response = requests.post(
            mcp_url,
            headers=headers,
            data=request_body,
            timeout=30
        )
        
        if response.status_code == 200:
            print("Success!")
            successful_url = mcp_url
            successful_headers = headers            
        else:
            print(f"Error: {response.status_code}")
            print(f"Response body: {response.text}")
            if response.status_code == 403 or "Invalid Bearer token" in response.text:
                print("403 Forbidden - Token may be expired, trying to get fresh token from Cognito...")
                # Try to get fresh bearer token from Cognito
                print(f"config: {config}")
                fresh_bearer_token = create_cognito_bearer_token(config)
                print(f"refreshed bearer token: {fresh_bearer_token}")
                if fresh_bearer_token:
                    print("Successfully obtained fresh token, updating headers and retrying...")
                    # Update headers with fresh token
                    headers["Authorization"] = f"Bearer {fresh_bearer_token}"
                    # Save the fresh token
                    secret_name = config['secret_name']
                    save_bearer_token(secret_name, fresh_bearer_token)
                    
                    # Retry the request with fresh token
                    response = requests.post(
                        mcp_url,
                        headers=headers,
                        data=request_body,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        print("Success with fresh token!")                        
                        successful_url = mcp_url
                        successful_headers = headers
                    else:
                        print(f"Still getting error with fresh token: {response.status_code}")
                        print(f"Response body: {response.text}")
                        return
                else:
                    print("Failed to get fresh token from Cognito")
                    return
            else:
                return
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    if not successful_url or not successful_headers:
        print("Failed to establish successful connection. Exiting.")
        return

    mcp_url = successful_url
    headers = successful_headers

    try:
        print(f"\n=== Attempting MCP Connection ===")
        print(f"URL: {mcp_url}")
        print(f"Timeout: 120 seconds")
        
        # Now try the MCP connection with better error handling
        print("1. Attempting streamablehttp_client connection...")
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
            read_stream, write_stream, _):
            
            print("2. streamablehttp_client connection successful!")
            print("3. Creating ClientSession...")
            
            async with ClientSession(read_stream, write_stream) as session:
                print("4. ClientSession created successfully!")
                print("5. Calling session.initialize()...")
                
                # Add timeout for initialize
                try:
                    await asyncio.wait_for(session.initialize(), timeout=60)
                    print("6. session.initialize() successful!")
                except asyncio.TimeoutError:
                    print("session.initialize() timeout (60s)")
                    return
                except Exception as init_error:
                    print(f"session.initialize() failed: {init_error}")
                    print(f"Error type: {type(init_error)}")
                    return
                
                print("7. Calling session.list_tools()...")
                
                # Add timeout for list_tools
                try:
                    tool_result = await asyncio.wait_for(session.list_tools(), timeout=60)
                    print(f"8. session.list_tools() successful!")
                    print(f"\nAvailable tools: {len(tool_result.tools)}")
                    for tool in tool_result.tools:
                        print(f"  - {tool.name}: {tool.description[:100]}...")
                except asyncio.TimeoutError:
                    print("session.list_tools() timeout (60s)")
                    return
                except Exception as tools_error:
                    print(f"session.list_tools() failed: {tools_error}")
                    print(f"Error type: {type(tools_error)}")
                    return
                                
                # Test retrieve function
                print("\n=== Testing retrieve function ===")
                params = {
                    "action": "HAPPY"
                }
                
                try:
                    targret_name = config['target_name']
                    tool_name = f"{targret_name}___command"

                    result = await asyncio.wait_for(session.call_tool(tool_name, params), timeout=30)
                    print(f"command result: {result}")
                    
                    if hasattr(result, 'content') and result.content:
                        for content in result.content:
                            if hasattr(content, 'text'):
                                print(f"Content: {content.text}")
                    else:
                        print("No content in result")
                except asyncio.TimeoutError:
                    print("retrieve function timeout (30s)")
                except Exception as retrieve_error:
                    print(f"retrieve function failed: {retrieve_error}")
                                
                print("\n=== MCP Connection Test Complete ===")
                
    except Exception as e:
        print(f"MCP connection failed: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
if __name__ == "__main__":
    asyncio.run(main())
