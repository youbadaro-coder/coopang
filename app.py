import streamlit as st
import time
from scraper import get_coupang_product_info, get_best_products
from generator import generate_blog_post

st.set_page_config(page_title="쿠팡 파트너스 마스터", page_icon="🛍️", layout="wide")

# ── 세션 상태 초기화 ───────────────────────────
if 'menu' not in st.session_state:
    st.session_state.menu = "URL로 글 생성"
if 'target_url' not in st.session_state:
    st.session_state.target_url = ""
if 'auto_generate' not in st.session_state:
    st.session_state.auto_generate = False

def start_auto_posting(url):
    """추천 리스트에서 클릭 시 호출되는 콜백 함수"""
    st.session_state.target_url = url
    st.session_state.menu = "URL로 글 생성"
    st.session_state.auto_generate = True

# ── 사이드바 설정 ──────────────────────────────
with st.sidebar:
    st.title("⚙️ 설정 및 메뉴")
    
    # 메뉴 선택 (key를 'menu'로 지정하여 세션 상태와 직접 연동)
    menu_options = ["URL로 글 생성", "🔥 베스트 상품 추천"]
    menu = st.radio("메뉴 선택", menu_options, key="menu")
    st.markdown("---")

    st.subheader("🤖 AI 모델 선택")
    ai_mode = st.radio(
        "글 생성에 사용할 AI",
        ["🆓 LM Studio (완전 무료)", "🔑 Gemini API (무료 키 필요)"],
        help="LM Studio는 인터넷 없이 내 컴퓨터에서 무료로 실행됩니다."
    )

    use_local = ai_mode.startswith("🆓")

    if use_local:
        st.success("✅ LM Studio 선택됨 - API 키 불필요!")
        st.caption("LM Studio가 실행 중이고 'Local Server'가 Start 상태여야 합니다.\n(포트: 1234)")
        api_key = None
    else:
        # 세션 상태에서 API 키 초기값 가져오기
        if 'gemini_api_key' not in st.session_state:
            st.session_state.gemini_api_key = ""
            
        api_key_input = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Google AI Studio에서 발급받은 API 키를 입력하세요. 무료로 하루 1,500회 사용 가능."
        )
        # 입력된 키 저장
        st.session_state.gemini_api_key = api_key_input
        api_key = api_key_input # 호환성 유지

        if api_key:
            if api_key.startswith("AIza"):
                st.success("✅ API 키 형식이 올바릅니다. (연결 준비 완료)")
                # 가용 모델 목록 표시 시도
                try:
                    from google import genai
                    client = genai.Client(api_key=api_key)
                    models = [m.name.replace("models/", "") for m in client.models.list() if 'generateContent' in m.supported_generation_methods]
                    if models:
                        st.info(f"📋 가용 모델: {', '.join(models[:5])}...")
                except Exception:
                    pass
            else:
                st.warning("⚠️ API 키 형식이 이상합니다. 확인해 주세요. (보통 AIza로 시작)")
        else:
            st.error("❌ API 키를 입력해 주세요.")
            
        st.markdown("[🔗 무료 API 키 발급받기](https://aistudio.google.com/app/apikey)")


# ── URL로 글 생성 ──────────────────────────────
if menu == "URL로 글 생성":
    st.title("🛍️ 쿠팡 상품 리뷰 자동 생성")
    
    # 1. API 키 확인 및 모델 목록 가져오기
    available_models = []
    if not use_local and api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            available_models = [m.name.replace("models/", "") for m in client.models.list() if 'generateContent' in m.supported_generation_methods]
        except Exception:
            pass

    # 2. 모델 선택 UI 및 안내 메시지
    if not use_local:
        if available_models:
            # 우선순위에 따른 기본값 설정
            default_idx = 0
            for i, m in enumerate(available_models):
                if '2.0-flash' in m or '1.5-flash' in m:
                    default_idx = i
                    break
            selected_model_id = st.selectbox("🎯 사용할 Gemini 모델 선택", available_models, index=default_idx)
        else:
            selected_model_id = "gemini-1.5-flash"
            st.warning("⚠️ 사용 가능한 모델 목록을 가져오지 못했습니다. 기본 모델(1.5-flash)을 시도합니다.")
        st.info("🔑 현재 **Gemini API** 모드 — 무료 한도(하루 1,500회) 내에서 사용 중입니다.")
    else:
        selected_model_id = None
        st.info("🆓 현재 **LM Studio** 모드 — API 키 없이 완전 무료로 실행 중입니다.")

    st.markdown("상품 링크를 입력하면 **네이버, 티스토리, 워드프레스** 맞춤형 글을 동시에 생성합니다.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. 쿠팡 링크 입력")
        # key를 'target_url'로 직접 지정하여 세션 상태와 동기화
        product_url = st.text_input(
            "쿠팡 상품 URL", 
            key="target_url",
            placeholder="https://www.coupang.com/vp/products/..."
        )
        generate_btn = st.button("🚀 블로그 글 생성하기", use_container_width=True, type="primary")

        # 자동 생성 트리거 또는 버튼 클릭 시
        if generate_btn or st.session_state.auto_generate:
            # 자동 생성 플래그는 한 번 사용 후 초기화
            current_url = st.session_state.target_url if st.session_state.auto_generate else product_url
            st.session_state.auto_generate = False
            
            # 유효성 검사
            if not use_local and not api_key:
                st.error("Gemini API 키를 먼저 입력해주세요. (또는 LM Studio 무료 모드로 전환하세요)")
                st.stop()
            if not current_url:
                st.warning("쿠팡 상품 URL을 입력해주세요.")
                st.stop()

            model_label = "LM Studio (로컬 무료)" if use_local else "Gemini API"
            
            # 진행 상태 바 초기화
            progress_bar = st.progress(0)
            status_text = st.empty()
            time_text = st.empty()
            
            start_time = time.time()
            
            def update_progress(percent, msg, est_total=None):
                progress_bar.progress(percent)
                elapsed = time.time() - start_time
                if est_total:
                    remaining = max(0, est_total - elapsed)
                    time_text.caption(f"⏱️ 경과 시간: {elapsed:.1f}초 | ⏳ 예상 남은 시간: {remaining:.1f}초")
                else:
                    time_text.caption(f"⏱️ 경과 시간: {elapsed:.1f}초")
                status_text.write(f"**[{percent}%]** {msg}")

            # 예상 소요 시간 설정 (LM Studio는 더 길게 잡음)
            est_total_time = 60 if use_local else 15

            update_progress(10, "🔍 상품 정보를 수집하는 중입니다...", est_total_time)
            product_info = get_coupang_product_info(current_url)

            if not product_info:
                st.error("상품 정보를 가져오지 못했습니다. URL을 확인해주세요.")
                st.stop()

            update_progress(30, f"✅ 상품명 확인: {product_info['title'][:30]}...", est_total_time)
            update_progress(40, f"✍️ {model_label} AI가 3가지 플랫폼용 글을 작성 중입니다. 잠시만 기다려주세요...", est_total_time)
            
            # 글 생성 실행 (선택된 모델 전달)
            blog_posts = generate_blog_post(
                product_info,
                api_key=api_key,
                use_local=use_local,
                gemini_model=selected_model_id if not use_local else None
            )

            update_progress(90, "🧹 생성된 글을 정리하고 서식을 적용하는 중입니다...", est_total_time)
            time.sleep(0.5)
            
            update_progress(100, "🎉 모든 플랫폼용 포스팅 생성이 완료되었습니다!", est_total_time)
            
            st.session_state['blog_posts'] = blog_posts
            st.session_state['current_product'] = product_info
            
            total_elapsed = time.time() - start_time
            st.success(f"✅ 총 {total_elapsed:.1f}초 만에 생성이 완료되었습니다.")

    with col2:
        st.subheader("2. 생성된 결과물")
        if 'blog_posts' in st.session_state:
            posts = st.session_state['blog_posts']
            tab1, tab2, tab3 = st.tabs(["🟢 네이버 블로그", "🍊 티스토리", "🔵 워드프레스"])

            with tab1:
                st.text_area("📋 복사용 텍스트", posts['naver'], height=300, key="res_naver")
                st.markdown("---")
                st.markdown("**📄 미리보기**")
                st.markdown(posts['naver'])

            with tab2:
                st.text_area("📋 복사용 마크다운", posts['tistory'], height=300, key="res_tistory")
                st.markdown("---")
                st.markdown("**📄 미리보기**")
                st.markdown(posts['tistory'])

            with tab3:
                st.text_area("📋 복사용 마크다운", posts['wordpress'], height=300, key="res_wordpress")
                st.markdown("---")
                st.markdown("**📄 미리보기**")
                st.markdown(posts['wordpress'])
        else:
            st.info("상품 링크를 입력하고 생성 버튼을 누르면 여기에 플랫폼별 글이 나타납니다.")


# ── 베스트 상품 추천 ────────────────────────────
elif menu == "🔥 베스트 상품 추천":
    st.title("🔥 현재 가장 인기 있는 상품 TOP 20")
    st.markdown("실시간으로 판매량과 관심도가 높은 상품들을 카테고리별로 확인하세요.")

    categories = {
        "가전디지털(종합)": 178155,
        "노트북/PC": 497035,
        "스마트폰": 497144,
        "스마트워치": 497152,
        "TV/영상가전": 178354,
        "냉장고": 403145,
        "주방용품":   185569,
        "뷰티":      176422,
        "식품":      194176,
        "생활용품":   115573,
        "패션의류":   564553,
    }

    # 필터 옵션
    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        selected_cats = st.multiselect(
            "확인할 카테고리",
            list(categories.keys()),
            default=["가전디지털(종합)", "주방용품"]
        )
    with filter_col2:
        price_filter = st.selectbox(
            "💰 가격 필터",
            ["전체 가격", "10만원 이상", "30만원 이상", "50만원 이상", "100만원 이상"],
        )

    # 가격 최솟값 매핑
    price_min_map = {
        "전체 가격":    0,
        "10만원 이상":  100_000,
        "30만원 이상":  300_000,
        "50만원 이상":  500_000,
        "100만원 이상": 1_000_000,
    }
    price_min = price_min_map[price_filter]

    def parse_price(price_str):
        """가격 문자열 → 정수 변환 (예: '189,000' → 189000)"""
        try:
            return int(price_str.replace(',', '').replace('원', '').strip())
        except Exception:
            return 0

    if st.button("📈 추천 상품 불러오기", type="primary"):
        for cat_name in selected_cats:
            with st.expander(f"📍 {cat_name} — {price_filter}", expanded=True):
                with st.spinner(f"'{cat_name}' 카테고리에서 베스트 상품을 수집 중입니다..."):
                    # limit을 100으로 설정 (필터링 모수를 늘리기 위함)
                    best_list = get_best_products(categories[cat_name], limit=100)

                    if best_list:
                        # 가격 필터 적용
                        if price_min > 0:
                            filtered = [item for item in best_list
                                        if parse_price(item['price']) >= price_min]
                        else:
                            filtered = best_list

                        # 상위 10개만 표시
                        filtered = filtered[:10]

                        if filtered:
                            for idx, item in enumerate(filtered, 1):
                                price_int = parse_price(item['price'])
                                price_display = f"{price_int:,}원" if price_int else item['price']

                                c1, c2, c3 = st.columns([0.5, 3, 1.2])
                                c1.markdown(f"### {idx}")
                                c2.markdown(f"**{item['title']}**")
                                c2.markdown(f"💰 **{price_display}**")
                                
                                # 바로 글쓰기 연결 버튼 (on_click 콜백 사용)
                                c3.button(
                                    "✍️ 포스팅 쓰기", 
                                    key=f"write_{idx}_{cat_name}",
                                    on_click=start_auto_posting,
                                    args=(item['url'],)
                                )
                                st.markdown("---")
                        else:
                            st.info(f"'{price_filter}' 조건에 해당하는 상품이 없습니다.")
                    else:
                        st.warning(f"{cat_name} 데이터를 가져오지 못했습니다. (쿠팡 일시적 차단 가능)")
