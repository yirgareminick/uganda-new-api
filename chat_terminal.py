import re
from openai import OpenAI, AssistantEventHandler
from typing_extensions import override

# Initialize OpenAI client with your API key
client = OpenAI(api_key="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")

# Function to interact with the assistant
def interact_with_assistant(prompt):
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

    # Create a message
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=prompt
    )

    # Event handler to process the response
    class EventHandler(AssistantEventHandler):
        @override
        def on_text_delta(self, delta, snapshot):
            # Clean up the output by removing citation and percentage
            cleaned_value = re.sub(r"【\d+:\d+†.*?】", "", delta.value)
            print(cleaned_value, end="", flush=True)

        def on_tool_call_delta(self, delta, snapshot):
            if delta.type == 'code_interpreter':
                if delta.code_interpreter.input:
                    print(delta.code_interpreter.input, end="", flush=True)

    # Stream the response
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant,
        event_handler=EventHandler(),
    ) as stream:
        stream.until_done()

# Terminal chat loop
def terminal_chat():
    print("Welcome to UgandAPI Chat! Type 'exit' to quit.\n")
    while True:
        prompt = input("You: ")
        if prompt.lower() == 'exit':
            print("Exiting chat. Goodbye!")
            break
        interact_with_assistant(prompt)
        print("\n")  # Newline for better formatting

if __name__ == "__main__":
    terminal_chat()