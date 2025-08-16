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
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain_community.retrievers import BM25Retriever
from typing import List, Optional
import re
import json

# Guarded prompt to reduce hallucinations and keep answers grounded in KB
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful, friendly business chatbot. Use a casual, human tone. "
     "Do not include technical implementation details. "
     "Never mention context, documents, knowledge base, or say phrases like 'based on the (provided) context', 'from the documents', or 'according to the KB'. "
     "If the context does not contain the answer, say you don't have that in the knowledge base and ask the user to specify a related business-focused topic. "
     "If the user confirms a previous offer (e.g., 'yes'), proceed with the offered details without asking again. "
     "Keep answers concise and clear, using Markdown and minimal emojis. "
     "Use the context below to help you answer."),
    ("human", "Context: {context}\n\nQuestion: {question}")
])

# Generic follow-up question rewriter (stateless; KB-agnostic)
followup_rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You convert a brief or ambiguous user message into a fully specified standalone question. "
     "Use the entire prior conversation (if provided), the previous user question, and the assistant's previous answer to infer intent and the most logical next step. "
     "If the previous answer offered to continue on a specific topic and the user replied with a confirmation (e.g., 'yes'), rewrite to explicitly request that next topic. "
     "Do not mention context or documents. Return ONLY the rewritten standalone question."),
    ("human", "Current message: {question}\n\nPrevious user message: {prev_user}\n\nPrevious assistant message: {prev_answer}\n\nConversation so far:\n{history}")
])

# Intent router to understand if the user is asking a question, giving thanks, small talk, asking for suggestions, etc.
intent_router_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You analyze the conversation and classify the user's current message. "
     "Return strict JSON with keys: intent (one of: 'qa', 'suggestion', 'recommendation', 'gratitude', 'greeting', 'goodbye', 'small_talk', 'clarification', 'confirm'), and target (string or null). "
     "If the user confirms (e.g., 'yes'), set intent to 'confirm' and set target to the most logical next topic inferred from the last assistant message. "
     "If it's a suggestion/recommendation request, set intent accordingly and make target a clear, standalone question we can answer with the knowledge base. "
     "Do NOT include any extra text outside the JSON."),
    ("human", "Current message: {question}\n\nPrevious user message: {prev_user}\n\nPrevious assistant message: {prev_answer}\n\nConversation so far:\n{history}")
])

def humanize_answer(text: str) -> str:
    if not text:
        return text
    patterns = [
        r"^\s*based on (the )?(provided )?context[:,]?\s*",
        r"^\s*from (the )?(provided )?(documents|context|kb|knowledge base)[:,]?\s*",
        r"^\s*according to (the )?(documents|context|kb|knowledge base)[:,]?\s*",
        r"^\s*given (the )?(context|documents)[:,]?\s*",
    ]
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def build_conversation_snippet(history: Optional[List["Message"]], max_messages: int = 10, max_chars: int = 1200) -> str:
    if not history:
        return ""
    recent = history[-max_messages:]
    parts: List[str] = []
    total = 0
    for m in recent:
        role = "User" if (m.role or "").lower().startswith("user") else "Assistant"
        content = (m.content or "").strip()
        if not content:
            continue
        line = f"{role}: {content}"
        if total + len(line) > max_chars:
            break
        parts.append(line)
        total += len(line)
    return "\n".join(parts)


def parse_intent(raw_content: str) -> dict:
    try:
        return json.loads(raw_content)
    except Exception:
        # Try to extract JSON block
        try:
            start = raw_content.find('{')
            end = raw_content.rfind('}')
            if start != -1 and end != -1 and end > start:
                return json.loads(raw_content[start:end+1])
        except Exception:
            pass
    return {"intent": "qa", "target": None}

load_dotenv()
openrouter_key = os.getenv("OPENROUTER_API_KEY")
api_key = openrouter_key or os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_BASE_URL", os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1"))

model_name = os.getenv("LLM_MODEL", "anthropic/claude-3.5-sonnet")
max_tokens = int(os.getenv("LLM_MAX_TOKENS", "400"))

default_headers = {
    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost"),
    "X-Title": os.getenv("OPENROUTER_APP_NAME", "Superion AI Chatbot"),
}

db = None
qa_chain = None
llm = None
followup_rewriter = None
intent_router_chain = None
hybrid_retriever: Optional[EnsembleRetriever] = None
_documents_cache: Optional[List[Document]] = None

def build_vectorstore_and_chain() -> None:
    global db, qa_chain, llm, followup_rewriter, intent_router_chain, _documents_cache, hybrid_retriever

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

    # 2. Split into chunks with better parameters
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    documents = splitter.split_documents(docs)
    if not documents:
        documents = [Document(page_content="")]  # ensure FAISS can be initialized
    _documents_cache = documents

    # 3. Embeddings
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 4. Dense index (FAISS)
    db = FAISS.from_documents(documents, embedding)

    # 5. LLM (configurable)
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        default_headers=default_headers,
        temperature=0.1,
        max_tokens=max_tokens,
    )

    # 6. Fast compression via embeddings filter (no extra LLM call)
    embeddings_filter = EmbeddingsFilter(embeddings=embedding, similarity_threshold=0.2)

    # 7. Hybrid retrieval: FAISS (dense) + BM25 (sparse) with lower k for speed
    faiss_retriever = db.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 8,
            "fetch_k": 30,
        },
    )
    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 8

    hybrid_retriever = EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[0.6, 0.4],
    )

    compression_retriever = ContextualCompressionRetriever(
        base_compressor=embeddings_filter,
        base_retriever=hybrid_retriever,
    )

    # 8. Retrieval QA (no source docs to reduce payload)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=compression_retriever,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=False,
    )

    # 9. Follow-up rewriter and router
    followup_rewriter = followup_rewrite_prompt | llm
    intent_router_chain = intent_router_prompt | llm


app = FastAPI()

@app.on_event("startup")
def on_startup() -> None:
    try:
        build_vectorstore_and_chain()
        print("Enhanced vector store and QA chain initialized (hybrid retriever)")
    except Exception as e:
        print(f"Startup initialization error: {e}")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class Question(BaseModel):
    query: str
    prev_user_query: Optional[str] = None
    prev_assistant_answer: Optional[str] = None
    history: Optional[List[Message]] = None

class ChatResponse(BaseModel):
    answer: str
    confidence: str

@app.post("/ask", response_model=ChatResponse)
async def ask_question(payload: Question):
    print("Received query:", payload.query)
    try:
        if qa_chain is None or hybrid_retriever is None or intent_router_chain is None:
            build_vectorstore_and_chain()

        history_snippet = build_conversation_snippet(payload.history)

        # Intent routing
        intent = {"intent": "qa", "target": None}
        try:
            routed = intent_router_chain.invoke({
                "question": payload.query,
                "prev_user": payload.prev_user_query or "",
                "prev_answer": payload.prev_assistant_answer or "",
                "history": history_snippet,
            })
            intent = parse_intent(getattr(routed, "content", ""))
        except Exception:
            pass

        current_intent = (intent.get("intent") or "qa").lower()
        target = (intent.get("target") or "").strip()

        # Handle non-QA intents quickly without retrieval
        if current_intent in {"gratitude", "greeting", "small_talk"}:
            quick = "You're welcome! If you'd like, I can dive into pricing tiers, features, or strategy next."
            if current_intent == "greeting":
                quick = "Hi! How can I help you today?"
            return ChatResponse(answer=quick, confidence="ok")
        if current_intent == "goodbye":
            return ChatResponse(answer="Happy to help! If anything else comes up, just ping me. 👋", confidence="ok")

        # Build final query: prefer intent target; otherwise use LLM follow-up rewriter
        final_query = target if target else payload.query
        if (not target) and (payload.prev_user_query or payload.prev_assistant_answer or history_snippet):
            try:
                rewritten = followup_rewriter.invoke({
                    "question": payload.query,
                    "prev_user": payload.prev_user_query or "",
                    "prev_answer": payload.prev_assistant_answer or "",
                    "history": history_snippet,
                })
                rq = getattr(rewritten, "content", "").strip()
                if rq and rq.lower() != (payload.query or "").strip().lower():
                    final_query = rq
                    print("LLM rewrite to:", final_query)
            except Exception:
                pass

        # Retrieval query should be concise: use final_query only
        retrieval_query = final_query
        
        # The LLM question can include conversation augmentation to keep answers on-topic
        augmented_question = final_query
        inline_context_parts: List[str] = []
        if history_snippet:
            inline_context_parts.append(f"Conversation so far:\n{history_snippet}")
        if payload.prev_assistant_answer:
            snippet = payload.prev_assistant_answer.strip()
            if len(snippet) > 800:
                snippet = snippet[:800]
            inline_context_parts.append(f"Previous assistant message:\n{snippet}")
        if inline_context_parts:
            augmented_question = f"{final_query}\n\n" + "\n\n".join(inline_context_parts)

        # Quick KB coverage check using hybrid retriever on concise query
        try:
            hits = hybrid_retriever.invoke(retrieval_query)
        except Exception:
            hits = []

        if not hits:
            not_found = (
                "I couldn't find that in the knowledge base. "
                "Try asking about business strategy, EUC, GTM, pricing, PLG, market research, SaaS ops, or distributed work."
            )
            return ChatResponse(answer=not_found, confidence="not_found")

        # Build context from hits and ask the LLM
        context_text = "\n\n".join([getattr(d, "page_content", "") for d in hits[:8] if getattr(d, "page_content", "")])
        messages = prompt.format_messages(context=context_text, question=augmented_question)
        llm_resp = llm.invoke(messages)
        answer = getattr(llm_resp, "content", str(llm_resp))
        answer = humanize_answer(answer)

        return ChatResponse(answer=answer, confidence="high")

    except Exception as e:
        print("Error during invoke:", str(e))
        error_message = "I'm having trouble processing your request right now. Please try again in a moment."
        return ChatResponse(answer=error_message, confidence="error")

