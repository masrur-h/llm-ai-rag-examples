"""
Demo 7.2 – LangGraph Persistence with SQLite

This is a TEMPLATE for when langgraph-checkpoint-sqlite is installed.

To use this file:
1. Install the SQLite checkpoint package:
   pip install langgraph-checkpoint-sqlite

2. Uncomment the imports and checkpointer code below

3. Run the script normally

The rest of the code remains identical to demo7-persistence.py or demo7.1-persistence-agent.py.
This demonstrates how easy it is to swap from MemorySaver to SqliteSaver.
"""

# STEP 1: Install the package first
# ─────────────────────────────────────────────────────────────────────────────
# pip install langgraph-checkpoint-sqlite

# STEP 2: Uncomment these imports when ready
# ─────────────────────────────────────────────────────────────────────────────
# import sqlite3
# from langgraph.checkpoint.sqlite import SqliteSaver

from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver  # Using MemorySaver for now
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage


# ─── State ────────────────────────────────────────────────────────────────────

class State(TypedDict):
    messages: Annotated[list, add_messages]


# ─── LLM ──────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")


# ─── Single node: call the LLM ───────────────────────────────────────────────

def chat(state: State) -> dict:
    """Send the full conversation history to the LLM and append its reply."""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# ─── Graph ────────────────────────────────────────────────────────────────────

builder = StateGraph(State)
builder.add_node("chat", chat)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)


# ─── Checkpointer: Choose one ─────────────────────────────────────────────────

# OPTION 1: In-memory (current, works without additional packages)
checkpointer = MemorySaver()

# OPTION 2: SQLite (uncomment when langgraph-checkpoint-sqlite is installed)
# ──────────────────────────────────────────────────────────────────────────
# checkpointer = SqliteSaver(
#     conn=sqlite3.connect(".checkpoints/langgraph.db")
# )

graph = builder.compile(checkpointer=checkpointer)


# ─── Thread config ────────────────────────────────────────────────────────────

config = {"configurable": {"thread_id": "demo-session-1"}}


# ─── Demo ────────────────────────────────────────────────────────────────────

print("=" * 70)
print("CONVERSATION WITH PERSISTENT STATE")
print("=" * 70)
print(f"\nUsing: {'SqliteSaver (persistent)' if 'SqliteSaver' in str(checkpointer.__class__) else 'MemorySaver (in-memory)'}")
print(f"Database file: .checkpoints/langgraph.db" if 'SqliteSaver' in str(checkpointer.__class__) else "")
print("\n" + "=" * 70)

# First message
print("\nINTERACTION 1")
print("-" * 70)
print("USER: Hello, my name is Bumblebee Jack")
result = graph.invoke(
    {"messages": [HumanMessage(content="Hello, my name is Bumblebee Jack")]},
    config,
)
print(f"ASSISTANT: {result['messages'][-1].content}\n")

# Second message (same thread)
print("INTERACTION 2")
print("-" * 70)
print("USER: Tell a joke based on my name")
result = graph.invoke(
    {"messages": [HumanMessage(content="Tell a joke based on my name")]},
    config,
)
print(f"ASSISTANT: {result['messages'][-1].content}\n")

# Show conversation history
print("=" * 70)
print("FULL CONVERSATION HISTORY")
print("=" * 70)
state = graph.get_state(config)
for i, msg in enumerate(state.values["messages"], 1):
    role = "USER" if isinstance(msg, HumanMessage) else "ASSISTANT"
    print(f"\n[{i}] {role}:")
    print(f"    {msg.content[:80]}..." if len(msg.content) > 80 else f"    {msg.content}")

print("\n" + "=" * 70)
print("NOTE: With MemorySaver, this data is lost when the program exits.")
print("      With SqliteSaver, it persists in .checkpoints/langgraph.db")
print("=" * 70)


# ─── Tips for Using SqliteSaver ────────────────────────────────────────────────

def tips_for_sqlite():
    """
    When using SqliteSaver in production:

    1. Create checkpoints directory:
       import os
       os.makedirs(".checkpoints", exist_ok=True)

    2. Use connection pooling for multiple threads:
       from sqlite3 import connect
       conn = connect(".checkpoints/langgraph.db", check_same_thread=False)

    3. Enable WAL (Write-Ahead Logging) for better concurrency:
       conn.execute("PRAGMA journal_mode=WAL")

    4. Back up your database regularly:
       cp .checkpoints/langgraph.db .checkpoints/langgraph.db.backup

    5. For PostgreSQL persistence (production-recommended):
       pip install langgraph-checkpoint-postgres

       from langgraph.checkpoint.postgres import PostgresSaver
       import psycopg
       conn = psycopg.connect("postgresql://user:pass@localhost/dbname")
       checkpointer = PostgresSaver(conn)
    """
    print(tips_for_sqlite.__doc__)


# Uncomment to see production tips
# tips_for_sqlite()
