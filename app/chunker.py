from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.loader import Document


class Chunker:
    def __init__(self):
        settings = get_settings()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        chunked = []
        for doc in documents:
            parts = self.splitter.split_text(doc.content)
            total = len(parts)
            for idx, part in enumerate(parts):
                # Prepend file context header
                content_with_header = f"File: {doc.metadata['file_path']}\n\n{part}"
                chunked.append(Document(
                    content=content_with_header,
                    metadata={
                        **doc.metadata,
                        "chunk_index": idx,
                        "total_chunks": total,
                    },
                ))
        print(f"[chunker] Produced {len(chunked)} chunks from {len(documents)} documents")
        return chunked
