from supabase import create_client, Client

from app.config import get_settings
from app.loader import Document


class SupabaseVectorStore:
    TABLE = "documents"
    BATCH_SIZE = 50

    def __init__(self):
        settings = get_settings()
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    def store_documents(self, chunks: list[Document], embeddings: list[list[float]]) -> None:
        rows = []
        for chunk, embedding in zip(chunks, embeddings):
            rows.append({
                "content": chunk.content,
                "metadata": chunk.metadata,
                "embedding": embedding,
            })

        total_batches = (len(rows) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        for i in range(0, len(rows), self.BATCH_SIZE):
            batch = rows[i: i + self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            print(f"[vector_store] Inserting batch {batch_num}/{total_batches} ({len(batch)} rows)")
            self.client.table(self.TABLE).insert(batch).execute()

        print(f"[vector_store] Stored {len(rows)} chunks total")

    def search(
        self,
        query_embedding: list[float],
        repo_name: str,
        top_k: int = 5,
    ) -> list[dict]:
        result = self.client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "filter": {"repo_name": repo_name},
            },
        ).execute()
        return result.data or []

    def delete_repo(self, repo_name: str) -> int:
        result = (
            self.client.table(self.TABLE)
            .delete()
            .filter("metadata->>repo_name", "eq", repo_name)
            .execute()
        )
        deleted = len(result.data) if result.data else 0
        print(f"[vector_store] Deleted {deleted} documents for repo '{repo_name}'")
        return deleted

    def list_repos(self) -> list[dict]:
        result = self.client.table(self.TABLE).select("metadata").execute()
        rows = result.data or []

        repo_counts: dict[str, dict] = {}
        for row in rows:
            meta = row.get("metadata", {})
            name = meta.get("repo_name", "unknown")
            source = meta.get("source", "unknown")
            if name not in repo_counts:
                repo_counts[name] = {"repo_name": name, "document_count": 0, "source": source}
            repo_counts[name]["document_count"] += 1

        return list(repo_counts.values())
