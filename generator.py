import json
import requests
from google import genai

# ──────────────────────────────────────────
#  공통 프롬프트 빌더
# ──────────────────────────────────────────
def _build_prompt(product_info):
    title    = product_info.get('title', '상품명 없음')
    price    = product_info.get('price', '가격 정보 없음')
    features = product_info.get('features', [])
    url      = product_info.get('url', '')
    features_str = "\n".join([f"- {f}" for f in features]) if features else "- 정보 없음"

    return f"""당신은 쿠팡 파트너스 수익화를 위한 전문 블로그 포스팅 작가입니다.
다음 상품 정보를 바탕으로 네이버 블로그, 티스토리, 워드프레스 3가지 플랫폼에 맞는 리뷰 글을 각각 작성해주세요.

[상품 정보]
- 상품명: {title}
- 가격: {price}
- 상품 링크: {url}
- 주요 특징:
{features_str}

[작성 가이드라인]
1. 네이버 블로그: 친근한 말투(~해요, ~에요), 이모지 풍부, 내돈내산 느낌, 짧은 문장 위주.
2. 티스토리: 전문적인 말투(~합니다), SEO 최적화, 장단점 비교, 마크다운 헤딩 구조.
3. 워드프레스: 구글 SEO 최우선, 전문 키워드 배치, 서술형 가이드 형식.
공통: 글 마지막에 반드시 "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다." 포함.

[출력 형식] 아래 JSON만 출력하세요. 다른 설명 없이 JSON만.
{{
  "naver": "네이버 블로그 포스팅 내용",
  "tistory": "티스토리 포스팅 내용",
  "wordpress": "워드프레스 포스팅 내용"
}}"""


def _parse_json_result(text):
    """JSON 파싱 시도, 실패 시 텍스트 전체를 공통 결과로 반환"""
    try:
        return json.loads(text)
    except Exception:
        # JSON 블록만 추출 시도
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return {"naver": text, "tistory": text, "wordpress": text}


def _error_result(msg):
    return {"naver": msg, "tistory": msg, "wordpress": msg}


# ──────────────────────────────────────────
#  LM Studio (로컬 무료) - OpenAI 호환 API
#  기본 포트: localhost:1234
# ──────────────────────────────────────────
def generate_with_lmstudio(product_info, base_url="http://localhost:1234"):
    try:
        # 현재 로드된 모델 자동 감지
        models_resp = requests.get(f"{base_url}/v1/models", timeout=5)
        if models_resp.status_code != 200:
            return _error_result("❌ LM Studio에 연결했으나 모델 목록을 가져올 수 없습니다.")
        
        models = models_resp.json().get("data", [])
        if not models:
            return _error_result("❌ LM Studio에 로드된 모델이 없습니다.\nLM Studio를 열고 모델을 로드한 뒤 'Start Server'를 눌러주세요.")
        
        model_id = models[0]["id"]  # 첫 번째 로드된 모델 사용

        prompt = _build_prompt(product_info)
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "당신은 전문 블로그 포스팅 작가입니다. 요청된 JSON 형식만 출력합니다."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4096,
            },
            timeout=180  # 로컬 모델은 시간이 걸릴 수 있음
        )

        if response.status_code == 200:
            result_text = response.json()["choices"][0]["message"]["content"]
            return _parse_json_result(result_text)
        else:
            return _error_result(f"❌ LM Studio 오류 (HTTP {response.status_code})")

    except requests.exceptions.ConnectionError:
        return _error_result(
            "❌ LM Studio 서버에 연결할 수 없습니다.\n\n"
            "확인 방법:\n"
            "1. LM Studio 앱을 실행하세요.\n"
            "2. 좌측 메뉴에서 'Local Server' 탭 클릭\n"
            "3. 모델을 선택하고 'Start Server' 버튼을 누르세요.\n"
            "4. 포트가 1234인지 확인하세요."
        )
    except Exception as e:
        return _error_result(f"❌ LM Studio 오류: {str(e)}")


# ──────────────────────────────────────────
#  Gemini API (무료 키 필요)
# ──────────────────────────────────────────
def generate_with_gemini(product_info, api_key):
    if not api_key:
        return _error_result("❌ Gemini API 키가 입력되지 않았습니다.")
    try:
        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(product_info)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return _parse_json_result(response.text)
    except Exception as e:
        return _error_result(f"❌ Gemini 오류: {str(e)}")


# ──────────────────────────────────────────
#  통합 진입점
# ──────────────────────────────────────────
def generate_blog_post(product_info, api_key=None, use_local=False, lmstudio_url="http://localhost:1234"):
    """
    use_local=True  → LM Studio 로컬 모델 (완전 무료, API 키 불필요)
    use_local=False → Gemini API (무료 키 필요)
    """
    if use_local:
        return generate_with_lmstudio(product_info, base_url=lmstudio_url)
    else:
        return generate_with_gemini(product_info, api_key)
