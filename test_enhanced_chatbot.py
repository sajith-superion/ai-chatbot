#!/usr/bin/env python3
"""
Test script for the enhanced chatbot features (follow-up rewrite, no storage)
"""

import requests

BASE_URL = "http://localhost:8000"

def test_enhanced_chatbot():
    print("🚀 Testing Enhanced Chatbot (Follow-up rewrite)\n")

    # Step 1: Ask about pricing strategies
    r1 = ask_question({"query": "Tell me pricing strategies"})
    print("1) status:", r1.get("confidence"), "\n   ", trim(r1.get("answer")))

    # Step 2: Short follow-up with prev context provided
    r2 = ask_question({
        "query": "can you suggest any from this?",
        "prev_user_query": "Tell me pricing strategies",
        "prev_assistant_answer": r1.get("answer", "")
    })
    print("2) status:", r2.get("confidence"), "\n   ", trim(r2.get("answer")))

    # Out-of-scope example
    r3 = ask_question({"query": "Weather in NYC?"})
    print("3) status:", r3.get("confidence"), "\n   ", trim(r3.get("answer")))


def ask_question(payload: dict) -> dict:
    try:
        response = requests.post(f"{BASE_URL}/ask", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error:", e)
        return {"error": str(e)}


def trim(text: str, n: int = 160) -> str:
    t = (text or "").strip().replace("\n", " ")
    return t[:n] + ("..." if len(t) > n else "")

if __name__ == "__main__":
    print("Make sure your chatbot is running on http://localhost:8000")
    print("Start it with: uvicorn chatbot:app --reload\n")
    test_enhanced_chatbot()
