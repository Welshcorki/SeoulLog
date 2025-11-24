#!/bin/bash
# 검색 키워드 테스트 스크립트

echo "🔍 서울시의회 검색 시스템 테스트"
echo "=================================="
echo ""

BASE_URL="http://localhost:8000/api/search"

# Level 1: 완전 일치
echo "⭐ Level 1: 완전 일치"
echo "1. AI 경쟁력"
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{"query": "AI 경쟁력", "n_results": 3}' | jq '.total_results, .results[0].title'
echo ""

echo "2. 도서구입비"
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{"query": "도서구입비", "n_results": 3}' | jq '.total_results, .results[0].title'
echo ""

# Level 2: 의미 검색
echo "⭐⭐ Level 2: 의미 검색"
echo "3. 지하철"
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{"query": "지하철", "n_results": 3}' | jq '.total_results, .results[0].title'
echo ""

echo "4. 지속가능발전"
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{"query": "지속가능발전", "n_results": 3}' | jq '.total_results, .results[0].title'
echo ""

# Level 3: 복잡한 쿼리
echo "⭐⭐⭐ Level 3: 복잡한 쿼리"
echo "5. AI 윤리"
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{"query": "AI 윤리", "n_results": 3}' | jq '.total_results, .results[0].title'
echo ""

echo "6. 교육청 인공지능"
curl -s -X POST $BASE_URL \
  -H "Content-Type: application/json" \
  -d '{"query": "교육청 인공지능", "n_results": 3}' | jq '.total_results, .results[0].title'
echo ""

echo "=================================="
echo "✅ 테스트 완료"
