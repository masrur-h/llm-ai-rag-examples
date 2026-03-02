import os

if not os.environ.get('GOOGLE_API_KEY'):
    print("Google API key not set in environment variable GOOGLE_API_KEY.")
    exit(1)

# --- 1. LLM & Embeddings ---
# init_chat_model simplifies initialization across providers (OpenAI, Anthropic, Google, etc.)
from langchain.chat_models import init_chat_model
llm = init_chat_model('gemini-2.5-flash-lite', model_provider='google_genai')


# --- 2. Vector Store (ChromaDB with persistence) ---
from langchain_chroma import Chroma

CHROMA_PATH = "./chroma_db_data"
COLLECTION_NAME = "langchain_rag_demo"

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    persist_directory=CHROMA_PATH
)

# --- 3. Load & Split Documents ---
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

PDF_PATH = os.path.join(os.path.dirname(__file__), "../4.2-homework-started-chromadb-filter/Day4-Homework-chromadb-filter-exercises.pdf")

# Only index if collection is empty (avoids duplicates on re-runs)
if vector_store._collection.count() == 0:
    loader = PyPDFLoader(PDF_PATH)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"Split PDF into {len(chunks)} chunks.")

    vector_store.add_documents(chunks)
    print(f"Indexed {len(chunks)} chunks into ChromaDB.")
else:
    print(f"Collection already contains {vector_store._collection.count()} chunks. Skipping indexing.")

# --- 4. Build RAG Chain with LCEL (LangChain Expression Language) ---
# LCEL uses the | operator to compose components into a pipeline.
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

retriever = vector_store.as_retriever()

prompt = ChatPromptTemplate.from_template("""Answer the question using only the context below.

Context:
{context}

Question: {question}""")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Chain: retrieve context → format → fill prompt → call LLM → parse output
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# --- 5. Run ---
print("\n--- Invoke ---")
response = rag_chain.invoke("What metadata fields are available in the knowledge base?")
print(response)

print("\n--- Stream ---")
for chunk in rag_chain.stream("What is the idea of Exercise 4?"):
    print(chunk, end="", flush=True)
print()
