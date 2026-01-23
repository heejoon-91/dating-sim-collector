from services.chroma_service import ChromaService
from typing import Optional


class RAGService:
    def __init__(self):
        try:
            self.chroma_service = ChromaService()
        except Exception as e:
            print(f"ChromaService init failed: {e}")
            self.chroma_service = None

    def search_context(self, query: str, n_results: int = 3) -> Optional[str]:
        """
        Queries ChromaDB for similar conversations and formats them as a context string.
        """
        if not self.chroma_service:
            return None

        try:
            results = self.chroma_service.get_similar_conversations(query, n_results)
            if not results:
                return None

            context_parts = []
            for i, item in enumerate(results, 1):
                subject = item["metadata"].get("subject", "Unknown")
                dialogue = item["dialogue"]
                context_parts.append(f"예시 {i} (주제: {subject}):\n{dialogue}")

            return "\n\n".join(context_parts)
        except Exception as e:
            print(f"Search context failed: {e}")
            return None
