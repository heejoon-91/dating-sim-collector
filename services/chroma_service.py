"""
ChromaDB 벡터 데이터베이스 서비스 모듈

정제된 채팅 데이터를 임베딩하여 ChromaDB에 저장하고,
유사 대화를 검색하는 기능을 제공합니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions


class ChromaService:
    """ChromaDB 벡터 데이터베이스 서비스"""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: str = "chat_conversations",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        """
        ChromaDB 서비스 초기화

        Args:
            persist_dir: ChromaDB 저장 경로 (None이면 기본 경로 사용)
            collection_name: 컬렉션 이름
            embedding_model: 사용할 임베딩 모델
        """
        # 기본 저장 경로 설정
        if persist_dir is None:
            persist_dir = str(Path(__file__).parent.parent / "chroma_db")

        self.persist_dir = persist_dir
        self.collection_name = collection_name

        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False)
        )

        # 임베딩 함수 설정
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )

        # 컬렉션 가져오기 또는 생성
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        print(f"ChromaDB initialized at {persist_dir}")
        print(f"Collection '{collection_name}' has {self.collection.count()} documents")

    def add_conversations(
        self, conversations: List[Dict], batch_size: int = 100
    ) -> int:
        """
        대화 데이터를 벡터 DB에 추가합니다.

        Args:
            conversations: 대화 데이터 리스트
            batch_size: 배치 크기

        Returns:
            추가된 문서 수
        """
        added_count = 0

        for i in range(0, len(conversations), batch_size):
            batch = conversations[i : i + batch_size]

            ids = []
            documents = []
            metadatas = []

            for conv in batch:
                conv_id = conv.get("conversation_id", f"conv_{i + len(ids)}")
                dialogue = conv.get("dialogue", "")

                if not dialogue:
                    continue

                ids.append(conv_id)
                documents.append(dialogue)

                # 메타데이터 (ChromaDB는 중첩 객체를 지원하지 않으므로 평탄화)
                metadata = {
                    "platform": conv.get("platform", ""),
                    "subject": conv.get("subject", ""),
                    "speaker_type": conv.get("speaker_type", ""),
                    "source_file": conv.get("source_file", ""),
                    "turn_count": len(conv.get("turns", [])),
                }
                metadatas.append(metadata)

            if ids:
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
                added_count += len(ids)
                print(f"Added batch {i // batch_size + 1}: {len(ids)} documents")

        print(f"Total documents added: {added_count}")
        print(f"Collection now has {self.collection.count()} documents")

        return added_count

    def search(
        self,
        query: str,
        n_results: int = 5,
        platform_filter: Optional[str] = None,
        subject_filter: Optional[str] = None,
    ) -> Dict:
        """
        쿼리와 유사한 대화를 검색합니다.

        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            platform_filter: 플랫폼 필터 (KAKAO, FACEBOOK 등)
            subject_filter: 주제 필터

        Returns:
            검색 결과 (documents, distances, metadatas)
        """
        where_filter = None

        # 필터 구성
        if platform_filter or subject_filter:
            conditions = []
            if platform_filter:
                conditions.append({"platform": platform_filter})
            if subject_filter:
                conditions.append({"subject": {"$contains": subject_filter}})

            if len(conditions) == 1:
                where_filter = conditions[0]
            else:
                where_filter = {"$and": conditions}

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        return results

    def get_similar_conversations(self, query: str, n_results: int = 3) -> List[Dict]:
        """
        사용자 쿼리와 유사한 대화를 반환합니다.

        Args:
            query: 사용자 입력
            n_results: 반환할 대화 수

        Returns:
            유사 대화 리스트
        """
        results = self.search(query, n_results=n_results)

        conversations = []

        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                conv = {
                    "dialogue": doc,
                    "metadata": (
                        results["metadatas"][0][i] if results["metadatas"] else {}
                    ),
                    "distance": (
                        results["distances"][0][i] if results["distances"] else 0
                    ),
                }
                conversations.append(conv)

        return conversations

    def clear_collection(self) -> None:
        """컬렉션의 모든 문서를 삭제합니다."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"Collection '{self.collection_name}' cleared")

    def get_stats(self) -> Dict:
        """컬렉션 통계를 반환합니다."""
        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "persist_dir": self.persist_dir,
        }


def load_and_index_data(data_path: str, clear_existing: bool = False) -> ChromaService:
    """
    정제된 데이터를 로드하여 ChromaDB에 인덱싱합니다.

    Args:
        data_path: 정제된 데이터 파일 경로
        clear_existing: 기존 데이터 삭제 여부

    Returns:
        ChromaService 인스턴스
    """
    # ChromaDB 서비스 초기화
    service = ChromaService()

    if clear_existing:
        service.clear_collection()

    # 이미 데이터가 있으면 건너뛰기
    if service.collection.count() > 0:
        print(
            f"Collection already has {service.collection.count()} documents. Skipping indexing."
        )
        return service

    # 데이터 로드
    with open(data_path, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    print(f"Loaded {len(conversations)} conversations from {data_path}")

    # 인덱싱
    service.add_conversations(conversations)

    return service


def main():
    """테스트 및 인덱싱 실행"""
    script_dir = Path(__file__).parent
    data_path = (
        script_dir.parent / "preprocess" / "processed" / "chat_data_cleaned_v2.json"
    )

    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        print("Please run data_preprocessor.py first.")
        return

    # 데이터 인덱싱
    service = load_and_index_data(str(data_path), clear_existing=True)

    # 테스트 검색
    print("\n" + "=" * 60)
    print("테스트 검색")
    print("=" * 60)

    test_queries = ["안녕하세요", "오늘 뭐해?", "밥 먹었어?"]

    for query in test_queries:
        print(f"\n쿼리: '{query}'")
        results = service.get_similar_conversations(query, n_results=2)
        for i, conv in enumerate(results):
            print(f"\n  결과 {i+1} (거리: {conv['distance']:.4f}):")
            print(f"    플랫폼: {conv['metadata'].get('platform', 'N/A')}")
            print(f"    주제: {conv['metadata'].get('subject', 'N/A')}")
            dialogue_preview = (
                conv["dialogue"][:100] + "..."
                if len(conv["dialogue"]) > 100
                else conv["dialogue"]
            )
            print(f"    대화: {dialogue_preview}")


if __name__ == "__main__":
    main()
