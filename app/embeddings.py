import time

import google.generativeai as genai

from app.config import get_settings


class GeminiEmbedder:
    MODEL = "models/text-embedding-004"
    BATCH_SIZE = 100

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.GEMINI_API_KEY)

    def embed_text(self, text: str) -> list[float]:
        for attempt in range(2):
            try:
                result = genai.embed_content(model=self.MODEL, content=text)
                return result["embedding"]
            except Exception as e:
                if attempt == 0:
                    print(f"[embeddings] Retrying after error: {e}")
                    time.sleep(2)
                else:
                    raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        total_batches = (len(texts) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i: i + self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            print(f"[embeddings] Embedding batch {batch_num}/{total_batches} ({len(batch)} texts)")

            for attempt in range(2):
                try:
                    results = [
                        genai.embed_content(model=self.MODEL, content=text)["embedding"]
                        for text in batch
                    ]
                    embeddings.extend(results)
                    break
                except Exception as e:
                    if attempt == 0:
                        print(f"[embeddings] Batch error, retrying: {e}")
                        time.sleep(5)
                    else:
                        raise

            # Rate limiting: sleep between batches to respect free tier (15 req/min)
            if i + self.BATCH_SIZE < len(texts):
                time.sleep(1)

        return embeddings
