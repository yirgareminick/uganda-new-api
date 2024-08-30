from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid
import re
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override

# Initialize OpenAI client globally
client = OpenAI(api_key="your-api-key-here")

app = FastAPI(
    title="UgandAPI Chat",
    description="This API facilitates communication for our chat-based mobile application hosted in Android Studio.",
    version="1.0.0"
)

# Models
class ChatMessage(BaseModel):
    messageId: str
    sender: str
    content: str
    timestamp: datetime

class NewChatMessage(BaseModel):
    sender: str
    content: str

class UserCredentials(BaseModel):
    username: str
    password: str

class UserRegistration(BaseModel):
    username: str
    password: str
    email: str

class UserResponse(BaseModel):
    userId: str
    username: str
    email: str

class TokenResponse(BaseModel):
    token: str

chats = []
users = {}
tokens = {}

# Function to interact with the assistant
def interact_with_assistant(prompt):
    assistant = "asst_CzgIXeWbYvtd7iPEXZT6D9Zu"

    try:
        with open("thread_id.txt", "r") as file:
            thread_id = file.read().strip()
    except FileNotFoundError:
        thread = client.beta.threads.create()
        thread_id = thread.id
        with open("thread_id.txt", "w") as file:
            file.write(thread_id)

    class EventHandler(AssistantEventHandler):
        @override
        def on_text_delta(self, delta, snapshot):
            cleaned_value = re.sub(r"【\d+:\d+†.*?】", "", delta.value)
            self.response.append(cleaned_value)

        def on_tool_call_delta(self, delta, snapshot):
            if delta.type == 'code_interpreter':
                if delta.code_interpreter.input:
                    self.response.append(delta.code_interpreter.input)

    handler = EventHandler()
    handler.response = []

    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant,
        event_handler=handler,
    ) as stream:
        stream.until_done()

    return "".join(handler.response)

# Endpoints
@app.get("/chats", response_model=List[ChatMessage])
def get_chats():
    return chats

@app.post("/chats", response_model=ChatMessage, status_code=201)
def post_chat(new_message: NewChatMessage):
    # Interact with the OpenAI assistant
    response_content = interact_with_assistant(new_message.content)
    
    message = ChatMessage(
        messageId=str(uuid.uuid4()),
        sender=new_message.sender,
        content=response_content,
        timestamp=datetime.utcnow()
    )
    chats.append(message)
    return message

@app.get("/chats/{messageId}", response_model=ChatMessage)
def get_chat(messageId: str):
    for chat in chats:
        if chat.messageId == messageId:
            return chat
    raise HTTPException(status_code=404, detail="Message not found")

@app.post("/users/login", response_model=TokenResponse)
def login(user_credentials: UserCredentials):
    if user_credentials.username in users and users[user_credentials.username]["password"] == user_credentials.password:
        token = str(uuid.uuid4())
        tokens[token] = user_credentials.username
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/users/register", response_model=UserResponse, status_code=201)
def register(user_registration: UserRegistration):
    if user_registration.username in users:
        raise HTTPException(status_code=400, detail="Username already taken")
    userId = str(uuid.uuid4())
    users[user_registration.username] = {
        "userId": userId,
        "password": user_registration.password,
        "email": user_registration.email
    }
    return {
        "userId": userId,
        "username": user_registration.username,
        "email": user_registration.email
    }

# To run the FastAPI server: uvicorn main:app --reload