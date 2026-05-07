import streamlit as st
from scraper import get_coupang_product_info, get_best_products
from generator import generate_blog_post

st.set_page_config(page_title="쿠팡 파트너스 마스터", page_icon="🛍️", layout="wide")

# ── 세션 상태 초기화 ───────────────────────────
if 'menu' not in st.session_state:
    st.session_state.menu = "URL로 글 생성"
if 'target_url' not in st.session_state:
    st.session_state.target_url = ""

# ── 사이드바 설정 ──────────────────────────────
with st.sidebar:
    st.title("⚙️ 설정 및 메뉴")
    # 세션 상태를 index로 연결하여 메뉴 전환 제어
    menu_options = ["URL로 글 생성", "🔥 베스트 상품 추천"]
    menu_index = menu_options.index(st.session_state.menu)
    st.session_state.menu = st.radio("메뉴 선택", menu_options, index=menu_index)
    menu = st.session_state.menu
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
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="Google AI Studio에서 발급받은 API 키를 입력하세요. 무료로 하루 1,500회 사용 가능."
        )
        st.markdown("[🔗 무료 API 키 발급받기](https://aistudio.google.com/app/apikey)")


# ── URL로 글 생성 ──────────────────────────────
if menu == "URL로 글 생성":
    st.title("🛍️ 쿠팡 상품 리뷰 자동 생성")
    
    # 현재 사용 모델 뱃지
    if use_local:
        st.info("🆓 현재 **LM Studio** 모드 — API 키 없이 완전 무료로 실행 중입니다.")
    else:
        st.info("🔑 현재 **Gemini API** 모드 — 무료 한도(하루 1,500회) 내에서 사용 중입니다.")

    st.markdown("상품 링크를 입력하면 **네이버, 티스토리, 워드프레스** 맞춤형 글을 동시에 생성합니다.")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("1. 쿠팡 링크 입력")
        # 세션 상태에서 URL을 가져옴
        product_url = st.text_input("쿠팡 상품 URL", value=st.session_state.target_url, placeholder="https://www.coupang.com/vp/products/...")
        # URL이 수동으로 입력되면 세션 상태 업데이트
        st.session_state.target_url = product_url
        generate_btn = st.button("🚀 블로그 글 생성하기", use_container_width=True, type="primary")

        if generate_btn:
            # 유효성 검사
            if not use_local and not api_key:
                st.error("Gemini API 키를 먼저 입력해주세요. (또는 LM Studio 무료 모드로 전환하세요)")
                st.stop()
            if not product_url:
                st.warning("쿠팡 상품 URL을 입력해주세요.")
                st.stop()

            model_label = "LM Studio (로컬 무료)" if use_local else "Gemini API"
            with st.status(f"[{model_label}] 상품 정보 수집 및 글 생성 중...", expanded=True) as status:
                st.write("🔍 상품 정보를 수집하는 중입니다...")
                product_info = get_coupang_product_info(product_url)

                if not product_info:
                    status.update(label="데이터 수집 실패", state="error")
                    st.error("상품 정보를 가져오지 못했습니다. URL을 확인해주세요.")
                    st.stop()

                title_display = product_info['title'] if product_info['title'] else "(상품명 수집 불가 - 쿠팡 차단)"
                st.write(f"✅ 상품명: {title_display}")
                st.write(f"✅ 가격: {product_info['price'] or '수집 불가'}")
                st.write(f"✍️ [{model_label}] AI가 3가지 플랫폼용 글을 작성 중입니다...")

                blog_posts = generate_blog_post(
                    product_info,
                    api_key=api_key,
                    use_local=use_local
                )

                status.update(label="✅ 글 생성 완료!", state="complete")
                st.session_state['blog_posts'] = blog_posts
                st.session_state['current_product'] = product_info

    with col2:
        st.subheader("2. 생성된 결과물")
        if 'blog_posts' in st.session_state:
            posts = st.session_state['blog_posts']
            tab1, tab2, tab3 = st.tabs(["🟢 네이버 블로그", "🍊 티스토리", "🔵 워드프레스"])

            with tab1:
                st.text_area("📋 복사용 텍스트", posts['naver'], height=300)
                st.markdown("---")
                st.markdown("**📄 미리보기**")
                st.markdown(posts['naver'])

            with tab2:
                st.text_area("📋 복사용 마크다운", posts['tistory'], height=300)
                st.markdown("---")
                st.markdown("**📄 미리보기**")
                st.markdown(posts['tistory'])

            with tab3:
                st.text_area("📋 복사용 마크다운", posts['wordpress'], height=300)
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
                                
                                # 바로 글쓰기 연결 버튼
                                if c3.button("✍️ 포스팅 쓰기", key=f"write_{idx}_{cat_name}"):
                                    st.session_state.target_url = item['url']
                                    st.session_state.menu = "URL로 글 생성"
                                    st.rerun()
                                st.markdown("---")
                        else:
                            st.info(f"'{price_filter}' 조건에 해당하는 상품이 없습니다.")
                    else:
                        st.warning(f"{cat_name} 데이터를 가져오지 못했습니다. (쿠팡 일시적 차단 가능)")
