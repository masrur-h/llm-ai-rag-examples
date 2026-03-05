# Core LLM Wrappers Demo

This demo shows how **LangChain abstracts away provider differences** when working with Large Language Models (LLMs). 
By using the same API, you can easily swap between providers such as **OpenAI via Azure**, **Mistral**, and **Google Gemini** without rewriting your application logic.

---

## 🎯 Goal

Students will:

* Understand how `init_chat_model` provides a unified interface for different LLMs.
* Learn how to quickly test the same prompt across multiple providers.
* Appreciate how LangChain simplifies switching providers during prototyping or production.

---

## 🚀 Setup

1. Make sure you have API keys for the providers you want to test:

   * AzureOpenAI → `AZUREOPENAI_API_KEY`
   * Mistral → `MISTRAL_API_KEY`
   * Google Gemini → `GOOGLE_API_KEY`

2. Install dependencies:

```bash
pip install langchain langchain_openai langchain-mistralai langchain_google_genai
```


---

## 📚 Student Activity

1. Run the code with the same prompt across all three providers.
2. Compare the style, detail, and clarity of responses.
3. Change the prompt (e.g., ask for a code example, a summary, or a list of pros/cons).
4. Discuss:

   * Which provider gave the most useful answer for your use case?
   * How does LangChain make it easier to experiment?

---

## ✅ Key Takeaways

* **Same code, different providers:** No need to rewrite logic when switching LLMs.
* **Unified API:** `init_chat_model` provides consistent access to chat models.
* **Flexibility:** Choose the best model for your application with minimal effort.


