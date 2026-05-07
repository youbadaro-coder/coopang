import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_coupang_product_info(url):
    """
    쿠팡 상품 페이지에서 상품 정보를 스크래핑합니다.
    """
    options = Options()
    # options.add_argument('--headless') # 디버깅 및 차단 방지를 위해 헤드리스 비활성화
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 쿠팡 봇 차단 우회를 위한 User-Agent 설정
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(url)
        # 페이지 로딩 대기
        time.sleep(3) 
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 상품명 추출 (여러 선택자 시도)
        title = ""
        for selector in ['h1.product-title', 'h2.prod-buy-header__title', 'h2.product-title']:
            tag = soup.select_one(selector)
            if tag:
                title = tag.text.strip()
                break
            
        # 2. 가격 추출
        price = ""
        for selector in ['div.price-amount.final-price-amount', 'span.total-price > strong', 'span.price-value', 'strong.price-value']:
            tag = soup.select_one(selector)
            if tag:
                price = tag.text.strip()
                break
            
        # 3. 특장점/상세 설명 추출 (주요 스펙)
        features = []
        for selector in ['ul.twc-list-disc.twc-list-outside > li', 'ul.prod-description-attribute > li', 'div.product-description-attribute li']:
            feature_tags = soup.select(selector)
            if feature_tags:
                for tag in feature_tags:
                    features.append(tag.text.strip())
                break
            
        product_info = {
            "url": url,
            "title": title,
            "price": price,
            "features": features
        }
        
        return product_info
        
    except Exception as e:
        print(f"스크래핑 중 오류 발생: {e}")
        return None
        
    finally:
        if driver:
            driver.quit()

def get_best_products(category_id, limit=10):
    """
    쿠팡 베스트 페이지에서 인기 상품 리스트를 가져옵니다.
    """
    url = f"https://www.coupang.com/np/best100/bestseller/{category_id}"
    options = Options()
    # options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
    
        # 더 많은 상품(최대 100개)을 불러오기 위해 페이지 스크롤 다운
        time.sleep(2)
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        items = soup.select('ul#itemList > li, li.search-product, li.cntnt-list-item')
        products = []
        
        for i, item in enumerate(items[:limit]):
            # 제목 추출
            title_tag = item.select_one('div.name, .title, .product-title')
            # 가격 추출
            price_tag = item.select_one('strong.price-value, .price-value, .price-amount')
            # 링크 추출
            link_tag = item.select_one('a[href*="/vp/products/"], a.search-product-link, a.baby-product-link')
            
            if title_tag and price_tag and link_tag:
                title = title_tag.text.strip()
                price = price_tag.text.strip()
                href = link_tag['href']
                link = "https://www.coupang.com" + href if not href.startswith('http') else href
                
                products.append({
                    "rank": i + 1,
                    "title": title,
                    "price": price,
                    "url": link
                })
        
        return products
        
    except Exception as e:
        print(f"베스트 상품 로딩 중 오류 발생: {e}")
        return []
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    # 테스트용 코드
    # 1. 단일 상품 정보 테스트
    test_url = "https://www.coupang.com/vp/products/7335597976"
    info = get_coupang_product_info(test_url)
    print("단일 상품 테스트:", info)
    
    # 2. 베스트 상품 테스트 (가전디지털: 178155)
    best_info = get_best_products(178155, limit=5)
    print("베스트 상품 테스트:", best_info)
