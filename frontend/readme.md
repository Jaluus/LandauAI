# Landau Frontend

The Landau Chatbot from the 2nd Institute of Physics A.  

## Installation without Docker

The Code is tested with Python 3.12.5.  
It is strongly recommended to use python >= 3.12 due to the use of type hints.
Example installation with conda and a virtual environment on a linux system:

```bash
conda create -n landau_frontend python=3.12
conda activate landau_frontend
pip install -r requirements_frozen.txt
```

Then create a `.env` file next to the `.env.example` file where you can see the required environment variables.

You can create the `CHAINLIT_AUTH_SECRET` by running the following command in the root directory:

```bash
chainlit create-secret
```

Then copy the output and paste it into the `.env` file.

## Starting the App

There are two ways to start the app.

### Deploying directly with chainlit

You can directly deploy the app with chainlit by running the following command in the root directory:

```bash
chainlit run app.py --port=7998 -h
```

`-h` is used to host the app in headless mode.  
For more information type: `chainlit run --help`

### Deploying as a FastAPI Server

The other way is to mount the app to a FastAPI server.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

This is used to also handle authentication and other features on a different route.
You probably don't need this for the first steps.  
IMPORTANT: Only use 1 worker, as the app is using websocket connections there is no reliable way to handle multiple workers as sessions would need to be mapped to the same worker.
For more information visit this [Issue](https://github.com/Chainlit/chainlit/issues/719).
But I found out that 1 worker is more than enough to handle about 200+ students concurrently.

## Auth Configs

Currently the programm is configured to always use authentication.  
To remove this for testing you can go into the `app.py` and comment out the `@cl.password_auth_callback` to remove password authentication and the `@cl.header_auth_callback` to remove header token authentication.

## Data Persistence

To enable data persistence you can set the data persistence in the `.env` file to `true`.
You should also have a postgres database running.
The schema for the database can be found in the `frontend/datalayer/pginit/setup_database.sql` file.

This will enable the data persistence and the data will be stored in a postgres database.  
For more information visit the [chainlit guide](https://docs.chainlit.io/data-persistence/custom)

## Tool Implementation

To implement a new tool you can go into the `utils/tools.py` file and add a new function.

```python
@tool(args_schema=my_new_tool_args_schema)
async def my_new_tool(tool_arg1: str, tool_arg2: list[str], ...) -> str:
    """
    A good description of the tool, when the model should call it, what it returns and what it does.
    For a good guide read (https://docs.anthropic.com/en/docs/build-with-claude/tool-use#example-of-a-good-tool-description)
    """

    # If you want to have feedback in the frontend you can use the cl.Step context manager
    async with cl.Step(
        name="my_tool",
        language=None, # how the output should be formatted
        show_input=True, # if the step.input should be shown
        type="tool", # the type of the step, this is used for the data base as metadata
    ) as step:
        step.input = "A Query has been made"
        try:
            # Add your tool code here, for example a server call
            # return the result
            return "This is the result of the tool"
        except Exception as e:
            # If the tool fails you can return an error message
            return f"An error occured: {e}"
```

For the best results you should make sure that the tool always returns a string as this is feed to the LLM.  
Typically you also want a description of your input arguments.
For this you want to use an `args_schema` class.

```python
class my_new_tool_args_schema(BaseModel):
    tool_arg1: str = Field(
        description="A good description of the argument, what it is and what it does.",
    )
    tool_arg2: list[str] = Field(
        description="A good description of the argument, what it is and what it does.",
    )

```

Afterwards you need to write some validation logic for the model, it may happend that the model outputs the wrong arguments or datatypes for the function.  
You now need to head to `utils/tool_calling.py` and add a handler for your function:

```python
async def execute_tool_call(tool: ToolCall) -> None:
    
    ...

    # handle the arguments which the model calls
    # you may want to restrict the model calling certain values
    # you may also handle this directly in the tool itself
    async def handle_my_new_tool(
        args: dict,
        **kwargs,
    ) -> str:
    try:
        # its important you call the function with .arun(tool_input=args)
        # if your function is synchronous you can call it with .run(tool_input=args)
        tool_response = await my_new_tool.arun(tool_input=args)
    except ValidationError as e:
        tool_response = (
            f"my_new_tool call failed. Bad arguments. Error: {str(e)}"
        )

    return tool_response

    ...


    elif tool_name == "retrieve_table_of_contents":
        tool_response = await handle_retrieve_table_of_contents(tool_args)

    # here would be your new tool
    elif tool_name == "my_new_tool":
        tool_response = await handle_my_new_tool(tool_args)

    elif tool_name == "query_wolfram_alpha":
        tool_response = await handle_query_wolfram_alpha(tool_args)

    ...
```

Then you can bind the tool in the `app.py` file.

```python
from utils.tools import my_tool_function

...

model_with_tools = model.bind_tools(
    [
        ...,
        my_tool_function,
    ]
)
```
