from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import TextLoader, DirectoryLoader, PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts.chat import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful, friendly business chatbot having a real-time conversation with users. "
     "Use a casual and natural tone. Speak like a human. "
     "Don't mention 'based on the provided context' or any technical references. "
     "Make responses engaging and clear using **Markdown** formatting and relevant minimal **emojis**. "
     "Use the context below to help you answer."),
    ("human", "Context: {context}\n\nQuestion: {question}")
])

load_dotenv()
openrouter_key = os.getenv("OPENROUTER_API_KEY")
api_key = openrouter_key or os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_BASE_URL", os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"))

# Optional but recommended headers for OpenRouter routing/limits
default_headers = {
    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
    "X-Title": os.getenv("OPENROUTER_APP_NAME", "Superion AI Chatbot"),
}

db = None
qa_chain = None


def build_vectorstore_and_chain() -> None:
    global db, qa_chain

    if not api_key:
        raise RuntimeError(
            "Missing OPENROUTER_API_KEY (or OPENAI_API_KEY). Set it in your environment or .env file."
        )

    # 1. Load all documents from data/ (pdf, docx, txt)
    pdf_loader = DirectoryLoader("data", glob="**/*.pdf", loader_cls=PyPDFLoader)
    docx_loader = DirectoryLoader("data", glob="**/*.docx", loader_cls=Docx2txtLoader)
    txt_loader = DirectoryLoader(
        "data",
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = []
    for loader in (pdf_loader, docx_loader, txt_loader):
        try:
            docs.extend(loader.load())
        except Exception:
            continue

    # 2. Split into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    documents = splitter.split_documents(docs)
    if not documents:
        documents = [Document(page_content="")]  # ensure FAISS can be initialized

    # 3. Create embeddings (local HF model to avoid remote errors)
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 4. Store in FAISS
    db = FAISS.from_documents(documents, embedding)

    # 5. Load OpenRouter LLM
    llm = ChatOpenAI(
        model="anthropic/claude-3.5-sonnet",
        api_key=api_key,
        base_url=base_url,
        default_headers=default_headers,
    )

    # 6. Setup Retrieval QA
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=db.as_retriever(),
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt}
    )

app = FastAPI()


@app.on_event("startup")
def on_startup() -> None:
    try:
        build_vectorstore_and_chain()
        print("Vector store and QA chain initialized")
    except Exception as e:
        # Log and continue; requests will surface a helpful error
        print(f"Startup initialization error: {e}")

# Serve static widget assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# Optional: Allow cross-origin requests (for web UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Question(BaseModel):
    query: str

@app.post("/ask")
async def ask_question(payload: Question):
    print("Received query:", payload.query)
    try:
        if qa_chain is None:
            # Attempt lazy init
            build_vectorstore_and_chain()
        result = qa_chain.invoke({"query": payload.query})
        print("Answer:", result)
        if isinstance(result, dict) and "result" in result:
            return {"answer": result["result"]}
        return {"answer": result}
    except Exception as e:
        print("Error during invoke:", str(e))
        return {"error": "Internal server error. Check API key and OpenRouter settings.", "detail": str(e)}

