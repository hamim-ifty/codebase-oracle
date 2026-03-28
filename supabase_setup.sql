-- Enable the pgvector extension
create extension if not exists vector;

-- Create the documents table
create table if not exists documents (
    id        bigserial primary key,
    content   text        not null,
    metadata  jsonb       not null default '{}',
    embedding vector(768) not null,
    created_at timestamptz not null default now()
);

-- Index for fast cosine similarity search
create index if not exists documents_embedding_idx
    on documents
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- Index on metadata for repo filtering
create index if not exists documents_metadata_idx
    on documents
    using gin (metadata);

-- RPC function: match_documents
create or replace function match_documents(
    query_embedding vector(768),
    match_count     int     default 5,
    filter          jsonb   default '{}'
)
returns table (
    id         bigint,
    content    text,
    metadata   jsonb,
    similarity float
)
language sql stable
as $$
    select
        id,
        content,
        metadata,
        1 - (embedding <=> query_embedding) as similarity
    from documents
    where metadata @> filter
    order by embedding <=> query_embedding
    limit match_count;
$$;
