import sys
import time
import json
import contextlib
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
from langchain.chains.openai_functions import create_structured_output_runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel as LangchainBaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks import get_openai_callback
from app.utils.fetch_collection_data import PostmanCollectionFetcher
from app.utils.multistream import MultiStream
import requests
import pprint
from fastapi.responses import StreamingResponse
import asyncio
from typing import AsyncIterator
import traceback

from app.config import config

router = APIRouter()
log_messages = asyncio.Queue()

def fetch_collection_data():
    try:

        fetcher = PostmanCollectionFetcher(config["postman_api_key"], config["forked_uid"])
        collection_data = fetcher.get_collection()
        if not collection_data:
            raise HTTPException(status_code=500, detail="data from collection not retrieved successfully")
        api_documentation = json.dumps(collection_data, indent=4)
        print("data successfully retrieved from postman collection...")
        return api_documentation
    except Exception as e:
        print("fetch_collection_data error:", str(e))
        print(traceback.format_exc())
        raise

def extract_descriptions_from_collection(api_documentation):
    print("retrieving descriptions from the collection data...")
    # append desc to htis list:
    descriptions = []
    collection_data = json.loads(api_documentation)

    def extract_descriptions(item):
        # filter for api docs:
        if isinstance(item, dict):
            if 'name' in item and item['name'] == 'Text Search':
                if 'request' in item and 'description' in item['request']:
                    descriptions.append(item['request']['description'])
            if 'item' in item:
                for sub_item in item['item']:
                    extract_descriptions(sub_item)

    for item in collection_data['collection']['item']:
        extract_descriptions(item)
    
    if descriptions:
        return json.dumps(descriptions[0], indent=4)
    print("failed to retrieve description from postamn api")
    return None

# NOTE: some of the code sinppets such as the prompt templates were taken from the following github repo:
# Original source: https://github.com/anurag899/openAI-project/blob/main/Multi-Agent%20Coding%20Framework%20using%20LangGraph/LangGraph%20-%20Code%20Development%20using%20Multi-Agent%20Flow.ipynb


# programmer agent template:
code_gen_prompt = ChatPromptTemplate.from_template('''
**Role**: You are an expert software Python programmer. You need to develop Python code.

**Task**: As a programmer, you are required to complete the function. Use a Chain-of-Thought approach to break down the problem, create pseudocode, and then write the code in Python language. Ensure that your code is efficient, readable, and well-commented.

**Instructions**:
1. **Understand and Clarify**: Make sure you understand the task.
2. **Algorithm/Method Selection**: Decide on the most efficient way.
3. **Pseudocode Creation**: Write down the steps you will follow in pseudocode.
4. **Code Generation**: Translate your pseudocode into executable Python code.

*REQUIREMENT*
{requirement}. Please use the following API key: {api_key} in the Python script''')



class Code(LangchainBaseModel):
    code: str = Field(description="Detailed optimized error-free Python code based on the provided requirements")

class UpdateCode(LangchainBaseModel):
    code: str = Field(description="Updated Python code after handling execution errors")

class ExecutableCode(BaseModel):
    code: str

class SimpleModel(BaseModel):
    content: str

class ConnectionManager:
    def __init__(self):
        self.active_connections:list[WebSocket] =[]

    async def connect(self, websocket:  WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("websocket connection working...")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("websocket connection closed...")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
        print(f"broadcast ::: {message}")

manager = ConnectionManager()

@router.post("/set-credentials")
async def set_credentials(request: Request):
    data = await request.form()
    # config["langchain_api_key"] = null
    # config["google_maps_api_key"] = null
    # config["openai_api_key"] = null


    config["langchain_api_key"] = data.get("langchain-api-key")
    config["google_maps_api_key"] = data.get("google-maps-api-key")
    config["openai_api_key"] = data.get("openai-api-key")

    print("updates api keys...")
    return {"message": "credentials have been successfully updated..."}

@router.get("/logs")
async def stream_logs(request: Request):
    async def event_publisher() -> AsyncIterator[str]:
        while True:
            if not log_messages.empty():
                message = await log_messages.get()
                yield f"data: {message}\n"
            await asyncio.sleep(1)
    return StreamingResponse(event_publisher(), media_type="text/event-stream")

@router.post("/execute_code")
async def execute_user_code(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        code = data.get("code")
        
        if not code:
            raise HTTPException(status_code=400, detail="missing code params...")
        await log_message("executing your code...")

        try:
            exec_result = execute_generated_code(code, model=None, textQuery=None)
            await log_message("your code has been executed successfully...")
            await log_message("download the results.txt file to get your data...")
        except Exception as execution_error:
            print(f"code failed to execute, error: {execution_error}")
            await log_message(f"execution failed:   {execution_error}")

            exec_result = await retry_execution(code, str(execution_error), None, None, None, log_message)
        
        await log_message("execution completed successfully")
        return {"execution result": exec_result}
    
    except Exception as e:
        error_message = str(e)
        print("execute_user_code failed due to error :", error_message)
        await log_message(f"code failed to execute due to error: {error_message}")
        raise HTTPException(status_code=500, detail=f"internal server error:  {error_message}")
        # raise HTTPException(status_code=400, detail=f"internal server error:  {error_message}")

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"your message ::: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/query")
async def handle_query(query: dict, background_tasks: BackgroundTasks):

    if not config.get("langchain_api_key") or not config.get("google_maps_api_key") or not config.get("openai_api_key"):
        print("api keys wrongly configured ")
        raise HTTPException(status_code=400, detail="failed to set api keys. please set your API keys in the credentials page.")

    langchain_api_key = config["langchain_api_key"]
    google_maps_api_key = config["google_maps_api_key"]
    openai_api_key = config["openai_api_key"]
    # gchain_api_key = None
    # google_maps_api_key =None
    # openai_api_key =None

    textQuery = query.get("query")
    model = query.get("model")

    if not textQuery:
        print("missing query param...")
        raise HTTPException(status_code=400, detail="missing query param ")
    if model not in ["gpt-4-turbo", "gpt-4o", "gpt-4"]:
        print("model does not exist :", model)
        raise HTTPException(status_code=400, detail="model does not exist ")

    try:
        api_documentation = fetch_collection_data()
        if not api_documentation:
            raise HTTPException(status_code=500, detail=" failed to collect descriptions .")
        print("api docs and descriptions extracted successfully")
    except Exception as e:
        print("error while fetching collection data:", str(e))
        raise HTTPException(status_code=500, detail=f"error for fetch collection data: {str(e)}")

    async def log_message(message: str):
        await log_messages.put(message)

    try:
        await log_message(f"received the following query: {textQuery}")
        await log_message(f"processing your query with model:  {model}")
        await asyncio.sleep(2.2)
        await log_message("Generation completed")

        llm = ChatOpenAI(
            verbose=True, model=model, top_p=0.1, temperature=0, max_tokens=1024,
            streaming=True, callbacks=[StreamingStdOutCallbackHandler()],
            openai_api_key=openai_api_key
        )

        prompt = api_documentation + f"""
            Now use this information to update the following Python script to satisfy the following user request: {textQuery}, do not change the API Key or use undefined variables. Here is the Python script:
            import requests
            import pprint
            def call_endpoint(api_key):
                # API endpoint URL
                url = 'https://places.googleapis.com/v1/places:searchText'
                # Parameters for the POST request
                payload = {{
                    'textQuery': 'insert textquery',
                }}
                headers = {{
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Key': api_key,
                    'X-Goog-FieldMask': 'places.displayName,places.formattedAddress'
                }}
                # Making the POST request
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    pprint.pprint(data)
                else:
                    print(f'Failed to retrieve data: {{response.status_code}}, {{response.text}}')
            api_key = '{google_maps_api_key}'
            top_restaurants = call_endpoint(api_key)
            """

        await log_message("prompt has been generated for code execution.")

        coder = create_structured_output_runnable(Code, llm, code_gen_prompt)
        generated_code = coder.invoke({"requirement": prompt, "api_key": google_maps_api_key})
        # print("generated code : ", generated_code.code)
        await log_message("code has been successfully generated, attempting to execute the code...")

        try:
            exec_result = execute_generated_code(generated_code.code, model, textQuery)
            await log_message("First attempt of executing code has been completed successfully")
            await log_message("the results.txt file is ready and contains the relevant data")
        except Exception as initial_execution_error:
            await log_message(f"first attempt has failed due to error: {initial_execution_error}")
            exec_result = await retry_execution(generated_code.code, str(initial_execution_error), code_gen_prompt.messages, model, textQuery, log_message)

        return {"generated_code": generated_code.code, "execution_result": exec_result}

    except Exception as e:
        error_message = str(e)
        print("error on handle_query:", error_message)
        await log_message(f"error occurred: {error_message}")
        raise HTTPException(status_code=500, detail=f"internal server error: {error_message}")

def execute_generated_code(code, model, textQuery):
    try:
        print(f"executing generated code:  \n{code}")
        exec_globals = {"__builtins__": __builtins__, "requests": requests, "pprint": pprint}

        #NOTE: get stdout and stderr 
        results_file_path = '/Users/zac/Desktop/TurboAPI/results.txt'
        exec_start_time = time.time()
        with open(results_file_path, 'w') as f:
            with contextlib.redirect_stdout(MultiStream(sys.stdout, f)), contextlib.redirect_stderr(MultiStream(sys.stderr, f)):
                exec(code, exec_globals)
        exec_end_time = time.time()
        print(f"executing and capturing output took {exec_end_time - exec_start_time:.2f} seconds")

        read_start_time = time.time()
        with open(results_file_path, 'r') as f:
            output = f.read()
        read_end_time = time.time()
        print(f"reading output from file took {read_end_time - read_start_time:.2f} seconds")

        print("results.txt file is ready with your data.")
        return output

    except Exception as execution_error:
        print(f"code execution error: {execution_error}")
        raise execution_error

async def log_message(message: str):
    await log_messages.put(message)

async def retry_execution(code: str, error_message: str, first_prompt: str, model: str, textQuery: str, log_message, max_retries=5):
    retry_count = 0
    results_file_path = '/Users/zac/Desktop/TurboAPI/results.txt'
    exec_result = None

    while retry_count < max_retries:
        try:
            retry_count += 1
            await log_message(f"retry attempt {retry_count} started")

            # Set up the updated prompt using the original prompt, error message, and user query
            updated_prompt_template = ChatPromptTemplate.from_template(
                """

                    *Role*: As a Script Debugger and Enhancer, your primary 
                    responsibility is to iteratively refine and correct Python code based on execution
                    errors and prompt specifications. You are tasked with correcting a Python script, reading the resulting execution error, and updating the 
                    script accordingly to address the error while satisfying user queries.

                    - Read the execution error from the previously executed Python script and the prompt used and update the script accordingly.
                    *Instruction*:
                    *Python Code*:{code} 
                    *Execution error*: {error_message}
                    *Previous prompt - in 'template' value*: {first_prompt}
                    *Now use this information to update the following Python script to satisfy the following user request/query: {textQuery}, do not change the API Key or use undefined variables.*
                """
            )
            
            llm = ChatOpenAI(model=model, temperature=0, max_tokens=1024, streaming=True, callbacks=[StreamingStdOutCallbackHandler()], openai_api_key=config["openai_api_key"])
            coder = create_structured_output_runnable(UpdateCode, llm, updated_prompt_template)
            params = {
                "code": code, 
                "error_message": error_message, 
                "first_prompt": first_prompt, 
                "textQuery": textQuery
            }


            # llm = ChatOpenAI(model=model, temperature=0, max_tokens=1024, streaming=True, callbacks=[StreamingStdOutCallbackHandler()], openai_api_key=config["openai_api_key"])
            # coder = create_structured_output_runnable(UpdateCode, llm, updated_prompt_template)
            # params = {
            #       "code": code, 
                #     "textQuery": textQuery
            # }
            await log_message(f"retry params: {params}")

            new_code_executable = coder.invoke(params)
            print(f"retry {retry_count},  new generated code:", new_code_executable.code)

            exec_globals = {"__builtins__": __builtins__, "requests": requests, "pprint": pprint}
            exec_start_time = time.time()
            with open(results_file_path, 'w') as results_file, contextlib.redirect_stdout(MultiStream(sys.stdout, results_file)), contextlib.redirect_stderr(MultiStream(sys.stderr, results_file)):
                exec(new_code_executable.code, exec_globals)
            exec_end_time = time.time()
            await log_message(f"retry execution took {exec_end_time - exec_start_time:.2f} seconds")

            read_start_time = time.time()
            with open(results_file_path, 'r') as f:
                exec_result = f.read()
            read_end_time = time.time()
            await log_message(f"total time to read output from file took {read_end_time - read_start_time:.2f} seconds")

            await log_message(f"retry count: {retry_count}, executed successfully, get your resutls from results.txt.")
            return exec_result

        except Exception as e:
            print(f"retry {retry_count} failed with error: {str(e)}")
            await log_message(f"retry {retry_count} failed: {e}")
            error_message = str(e)

        if retry_count >= max_retries:
            await log_message("the system has reached the maxium number of retry attempts, unable to execute the script successfully")
            raise Exception("the system has reached the maxium number of retry attempts, unable to execute the script successfully")

    return exec_result