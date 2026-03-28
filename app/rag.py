import google.generativeai as genai

from app.config import get_settings
from app.embeddings import GeminiEmbedder
from app.vector_store import SupabaseVectorStore

SYSTEM_PROMPT = """You are Codebase Oracle, an expert code assistant. You help developers understand codebases by answering their questions using the provided source code context.

Rules:
1. Only answer based on the provided context. If the context doesn't contain enough information, say so honestly.
2. Reference specific file paths when explaining code.
3. Use code snippets from the context when helpful.
4. Be concise but thorough. Explain the why not just the what.
5. If the question is about architecture or design patterns, explain how the pieces connect.
6. Format your response with markdown for readability."""


class RAGPipeline:
    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.embedder = GeminiEmbedder()
        self.vector_store = SupabaseVectorStore()
        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            system_instruction=SYSTEM_PROMPT,
        )

    def query(self, question: str, repo_name: str) -> dict:
        print(f"[rag] Embedding question: {question!r}")
        query_embedding = self.embedder.embed_text(question)

        print(f"[rag] Searching top-5 chunks for repo '{repo_name}'")
        results = self.vector_store.search(query_embedding, repo_name, top_k=5)

        if not results:
            return {
                "answer": "No relevant code was found in the repository for your question. Make sure you have ingested the repository first.",
                "sources": [],
                "question": question,
            }

        # Build numbered context block
        context_parts = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            file_path = meta.get("file_path", "unknown")
            similarity = r.get("similarity", 0.0)
            content = r.get("content", "")
            context_parts.append(
                f"[{i}] File: {file_path} (similarity: {similarity:.3f})\n{content}"
            )
        context_block = "\n\n---\n\n".join(context_parts)

        user_prompt = (
            f"Context from the codebase:\n\n{context_block}\n\n"
            f"Question: {question}\n\n"
            "Provide a clear, helpful answer referencing the relevant source files."
        )

        print("[rag] Calling Gemini Flash for answer generation")
        response = self.model.generate_content(user_prompt)
        answer = response.text

        sources = []
        for r in results:
            meta = r.get("metadata", {})
            content = r.get("content", "")
            sources.append({
                "file_path": meta.get("file_path", "unknown"),
                "chunk_preview": content[:200],
                "similarity": r.get("similarity", 0.0),
            })

        return {"answer": answer, "sources": sources, "question": question}
