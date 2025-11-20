import sqlite3
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent.parent))

conn = sqlite3.connect('data/sqlite_DB/agendas.db')
cursor = conn.cursor()

# 총 안건 수
cursor.execute('SELECT COUNT(*) FROM agendas')
total = cursor.fetchone()[0]
print(f'📊 총 안건 수: {total}개\n')

# 샘플 안건
cursor.execute('SELECT agenda_id, agenda_title, main_speaker, chunk_count FROM agendas LIMIT 5')
print('📋 샘플 안건:')
for row in cursor.fetchall():
    print(f'  - ID: {row[0]}')
    print(f'    제목: {row[1][:60]}...')
    print(f'    주 발언자: {row[2]}')
    print(f'    청크 수: {row[3]}개')
    print()

# ChromaDB 확인
import chromadb
from chromadb.config import Settings
from utils.custom_openai_embedding import CustomOpenAIEmbeddingFunction
import os
from dotenv import load_dotenv

load_dotenv()

chroma_client = chromadb.PersistentClient(
    path="./data/chroma_db",
    settings=Settings(anonymized_telemetry=False)
)
openai_ef = CustomOpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)
collection = chroma_client.get_collection(
    name="seoul_council_meetings",
    embedding_function=openai_ef
)

print(f'📦 ChromaDB 총 청크 수: {collection.count()}개\n')

# 샘플 청크 확인
results = collection.get(
    limit=3,
    include=["metadatas"]
)

print('📋 샘플 청크 메타데이터:')
for i, metadata in enumerate(results['metadatas'], 1):
    print(f'  청크 {i}:')
    print(f'    agenda_id: {metadata.get("agenda_id", "없음")}')
    print(f'    agenda: {metadata.get("agenda", "없음")[:50]}...')
    print(f'    speaker: {metadata.get("speaker", "없음")}')
    print()

conn.close()
