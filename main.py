import os  # To interact with the operating system and environment variables.
import streamlit as st  # To create and run interactive web applications directly through Python scripts.
from pathlib import Path  # To provide object-oriented filesystem paths, enhancing compatibility across different operating systems.
from dotenv import load_dotenv  # To load environment variables from a .env file into the system's environment for secure and easy access.
from groq import Groq  # To interact with Groq's API for executing machine learning models and handling data operations.
from pinecone import Pinecone
from langchain_huggingface import HuggingFaceEmbeddings

# Load environment variables from .env at the project root
project_root = Path(__file__).resolve().parent
load_dotenv(project_root / ".env")

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("new-medical-bot")

class GroqAPI:
    """Handles API operations with Groq to generate chat responses."""
    def __init__(self, model_name: str):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model_name = model_name

# Internal method to fetch responses from the Groq API
    def _response(self, message):
        """Fetches a response from the Groq API given a message."""
        return self.client.chat.completions.create(
            model=self.model_name,
            messages=message,
            temperature=0,
            max_tokens=1000,
            stream=True,
            stop=None,
        )

# Generator to stream responses from the API
    def response_stream(self, message):        
        for chunk in self._response(message):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

class Message:
    """Manages chat messages within the Streamlit UI."""
    system_prompt = "Tu es un professionnel de la programmation qui aide à apprendre à programmer. Répondre brièvement en francais aux entrées de l'utilisateur."

# Initialize chat history if it doesn't exist in session state
    def __init__(self):
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "system", "content": self.system_prompt}]

# Add a new message to the session state
    def add(self, role: str, content: str):
        st.session_state.messages.append({"role": role, "content": content})

# Display all past messages in the UI, skipping system messages
    def display_chat_history(self):
        for message in st.session_state.messages:
            if message["role"] == "system":
                continue
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

# Stream API responses to the Streamlit chat message UI
    def display_stream(self, generater):
        with st.chat_message("assistant"):
            return st.write_stream(generater)

class ModelSelector:
    """Allows the user to select a model from a predefined list."""
    def __init__(self):
        # List of available models to choose from
        self.models = ["llama3-70b-8192","llama3-8b-8192","mixtral-8x7b-32768", "deepseek-r1-distill-llama-70b"]

# Display model selection in a sidebar with a title
    def select(self):
        with st.sidebar:
            st.sidebar.title("🖥️ Chatbot éducatif pour apprendre à programmer")
            return st.selectbox("Choisir un LLm:", self.models)

class Retriever:
    def __init__(self):
        self.embed_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en",
            multi_process=True,
            encode_kwargs={"normalize_embeddings": True},  # Set `True` for cosine similarity
        )

    def retrieve_context(self, query, top_k=3):
        query_embedding = self.embed_model.embed_query(query)
        results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        context = "\n".join([match["metadata"]["text"] for match in results["matches"]])
        return context if context else "No relevant context found."

# Entry point for the Streamlit app
def main():
    user_input = st.chat_input("Que voulez-vous savoir...")
    model = ModelSelector()
    selected_model = model.select()
    message = Message()
    retriever = Retriever()

# If there's user input, process it through the selected model
    if user_input:
        #context = self.retriever.retrieve_context(user_input)
        #full_prompt = f"Retrieved Context:\n{context}\n\nUser Query: {user_input}"
        llm = GroqAPI(selected_model)
        message.add("user", user_input)
        message.display_chat_history()
        response = message.display_stream(llm.response_stream(st.session_state.messages))
        message.add("assistant", response)

if __name__ == "__main__":
    main()