import json
import time
import openai

class NegotiationAgent:
    """
    NegotiationAgent wraps OpenAI's Assistant API to handle message generation for classified ads.
    It uses GPT-4 with the new Threads, Runs, and Tools (function calling) interface.
    """
    def __init__(self, model: str = "gpt-4-0613"):
        """
        Initialize the agent: create an assistant with specified model and tools.
        """
        # Create the assistant with instructions and a custom function tool for field extraction
        self.assistant = openai.beta.assistants.create(
            name="Kleinanzeigen Negotiation Assistant",
            instructions=(
                "You are an assistant that helps the user write a message to a seller on an online classifieds platform. "
                "Always respond in polite, formal German (use 'Sie'). The user will provide the advertisement details (title, description, price, etc.) "
                "and specify what they want to discuss (e.g., negotiating price, scheduling a meeting, asking about condition). "
                "Use the provided details to compose a single well-written message addressing the seller. "
                "Include a polite greeting and cover all requested topics. Do not mention the analysis or any internal steps, just present the final message."
            ),
            model=model,
            # Define the custom function tool for extracting fields from listing text
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "extract_fields",
                        "description": "Extract key fields from a furniture listing text (like title, price, condition, dimensions, location).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "The raw text of the classified ad listing (including title, price, description, etc.)."
                                }
                            },
                            "required": ["text"]
                        }
                    }
                }
            ]
        )
        self.assistant_id = self.assistant.id
        self.current_thread_id = None

    def start_new_thread(self):
        """
        Create a new conversation thread for a fresh context (e.g., a new listing).
        """
        thread = openai.beta.threads.create()
        self.current_thread_id = thread.id
        return self.current_thread_id

    def add_user_message(self, content: str):
        """
        Add a user message to the current thread. 
        Ensure a thread is started before calling this.
        """
        if not self.current_thread_id:
            raise RuntimeError("Thread not initialized. Call start_new_thread() first.")
        openai.beta.threads.messages.create(
            thread_id=self.current_thread_id,
            role="user",
            content=content
        )

    def run_assistant(self):
        """
        Run the assistant on the current thread. This will process the conversation 
        (including any function calls) and return the assistant's response text.
        """
        if not self.current_thread_id:
            raise RuntimeError("Thread not initialized. Cannot run assistant without a thread.")
        # Start a new run for this thread using our assistant
        run = openai.beta.threads.runs.create(
            thread_id=self.current_thread_id,
            assistant_id=self.assistant_id
        )
        # Poll the run until it is completed, handling function calls if required
        while True:
            # Refresh run status
            run = openai.beta.threads.runs.retrieve(
                thread_id=self.current_thread_id,
                run_id=run.id
            )
            if run.status == "completed":
                break
            if run.status == "failed" or run.status == "cancelled":
                raise RuntimeError(f"Assistant run {run.status}: {run.failure_reason if hasattr(run, 'failure_reason') else ''}")
            if run.status == "requires_action":
                # Check if we need to submit tool outputs (function call)
                if run.required_action.type == "submit_tool_outputs":
                    # There might be multiple tool calls required; handle each
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    outputs = []
                    for tool_call in tool_calls:
                        func_name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        if func_name == "extract_fields":
                            # Call the actual extraction function with provided arguments
                            text = args.get("text", "")
                            result = self._tool_extract_fields(text)
                            # Prepare tool output as a JSON string
                            output_str = json.dumps(result, ensure_ascii=False)
                            outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": output_str
                            })
                        else:
                            # If an unknown tool was requested (not expected here)
                            outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": f'{{"error": "Tool {func_name} not implemented"}}'
                            })
                    # Submit all tool outputs back to the assistant and continue the run
                    run = openai.beta.threads.runs.submit_tool_outputs(
                        thread_id=self.current_thread_id,
                        run_id=run.id,
                        tool_outputs=outputs
                    )
                    # Continue polling in the next loop iteration
                    continue
                else:
                    # If there are other required actions (e.g., file upload), handle if needed
                    raise RuntimeError(f"Unhandled required action: {run.required_action.type}")
            # If still in progress, wait briefly and loop
            time.sleep(0.2)
        # Once run is completed, retrieve the messages and find the assistant's latest response
        messages = openai.beta.threads.messages.list(thread_id=self.current_thread_id)
        assistant_message = ""
        for msg in messages.data:
            if msg.role == "assistant":
                # Concatenate all text parts of the assistant's message content
                for content_part in msg.content:
                    if hasattr(content_part, "text") and content_part.text is not None:
                        assistant_message += content_part.text.value
                # Break at the first assistant message (messages list is likely reverse-chronological)
                break
        return assistant_message

    def _tool_extract_fields(self, text: str) -> dict:
        """
        Internal function that extracts fields from the listing text.
        This is the implementation of the 'extract_fields' tool that the assistant can call.
        Returns a dictionary of extracted fields: title, price, condition, dimensions, location.
        """
        fields = {
            "title": None,
            "price": None,
            "condition": None,
            "dimensions": None,
            "location": None,
            "description": None
        }
        if not text:
            return fields
        # Look for known field labels first (if text is structured with labels)
        lines = text.splitlines()
        for line in lines:
            lower = line.strip().lower()
            if lower.startswith("title:") or lower.startswith("titel:"):
                fields["title"] = line.split(":", 1)[1].strip()
            elif lower.startswith("price:") or lower.startswith("preis:"):
                fields["price"] = line.split(":", 1)[1].strip()
            elif lower.startswith("condition:") or lower.startswith("zustand:"):
                fields["condition"] = line.split(":", 1)[1].strip()
            elif lower.startswith("dimensions:") or lower.startswith("maße:") or lower.startswith("größe:"):
                fields["dimensions"] = line.split(":", 1)[1].strip()
            elif lower.startswith("location:") or lower.startswith("ort:"):
                fields["location"] = line.split(":", 1)[1].strip()
        # If some fields are still None, try to find patterns in the whole text
        full_lower = text.lower()
        if fields["price"] is None:
            # Find price as a number followed by euro symbol
            import re
            price_match = re.search(r'(\d[\d\.\, ]*)(?=\s*€)', text)
            if price_match:
                fields["price"] = price_match.group(1).strip()
        if fields["condition"] is None:
            # Look for common condition keywords in text
            for cond in ["neu", "neuwertig", "gebraucht", "gutem zustand", "top zustand", "einwandfrei"]:
                if cond in full_lower:
                    fields["condition"] = cond
                    break
        if fields["dimensions"] is None:
            # Look for pattern like '100x50x30 cm' in text
            import re
            dim_match = re.search(r'(\d+\s*x\s*\d+(\s*x\s*\d+)?\s*cm)', full_lower)
            if dim_match:
                fields["dimensions"] = dim_match.group(1)
        if fields["location"] is None:
            # Location might be difficult to parse generically; skip if not labeled
            pass
        # If title still None, assume first non-empty line is title
        if fields["title"] is None and lines:
            for line in lines:
                if line.strip():
                    fields["title"] = line.strip()
                    break
        # Treat the entire text as description (fallback)
        fields["description"] = text.strip()
        return fields
