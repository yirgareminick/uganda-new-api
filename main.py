import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid
import re
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override

# Initialize OpenAI client globally
client = OpenAI()

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
    thread_id: str

class NewChatMessage(BaseModel):
    sender: str
    content: str
    thread_id: str = None  # Optional field for existing threads

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
def interact_with_assistant(prompt, thread_id=None):
    assistant = "asst_gJkvVb6RSZj8BofmghLOnWVi"
    
     # If a thread already exists, use its ID; otherwise, create a new one
    try:
        with open("thread_id.txt", "r") as file:
            thread_id = file.read().strip()
    except FileNotFoundError:
        thread = client.beta.threads.create()
        thread_id = thread.id
        with open("thread_id.txt", "w") as file:
            file.write(thread_id)

    # Create a message before starting the stream
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    class EventHandler(AssistantEventHandler):
        @override
        def on_text_delta(self, delta, snapshot):
            cleaned_value = re.sub(r"【\d+:\d+†.*?】", "", delta.value)
            self.response.append(cleaned_value)

    handler = EventHandler()
    handler.response = []

    # Stream the response from the assistant
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant,
        event_handler=handler,
    ) as stream:
        stream.until_done()

    return "".join(handler.response), thread_id

# Endpoints
@app.get("/chats", response_model=List[ChatMessage])
def get_chats():
    return chats

@app.post("/chats", response_model=ChatMessage, status_code=201)
def post_chat(new_message: NewChatMessage):
    # Write the incoming message data to a file
    with open("incoming_message.txt", "w") as file:
        file.write(f"Sender: {new_message.sender}\n")
        file.write(f"Content: {new_message.content}\n")
        file.write(f"Thread ID: {new_message.thread_id}\n")

    # Interact with the OpenAI assistant
    response_content, thread_id = interact_with_assistant(new_message.content, new_message.thread_id)
    
    message = ChatMessage(
        messageId=str(uuid.uuid4()),
        sender=new_message.sender,
        content=response_content,
        timestamp=datetime.utcnow(),
        thread_id=thread_id
    )
    chats.append(message)
    return message

@app.get("/chats/{messageId}", response_model=ChatMessage)
def get_chat(messageId: str):
    for chat in chats:
        if chat.messageId == messageId:
            return chat
    raise HTTPException(status_code=404, detail="Message not found")