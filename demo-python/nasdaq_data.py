# pandas.read_html을 위해 requests와 pandas import
import requests
import pandas as pd

# 나스닥 100 지수 구성 종목 티커 리스트 확보 함수
def get_nasdaq_100_tickers():

    print("나스닥 100 지수 구성 종목 크롤링 시작...")
    
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        
        # 웹 크롤링 차단되는 경우 User-Agent 헤더를 추가하여 요청. 
        # (웹사이트 서버가 일반 브라우저의 요청으로 인식하게 함)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # 1. requests를 사용하여 웹페이지 콘텐츠 요청
        response = requests.get(url, headers=headers)
        
        # 2. HTTP 요청 상태 확인 (요청 직후 HTTP 오류 검사 진행)
        response.raise_for_status()

        # 3. pandas.read_html로 HTML 내 모든 <table> 요소를 DataFrame 리스트로 변환
        tables = pd.read_html(response.text)
        print(f"-> 웹페이지에서 총 {len(tables)}개의 HTML 테이블 발견.")
        nasdaq_table = None

        # 4. DataFrame 리스트를 순회하며 'Ticker'와 'Company' 컬럼을 가진 표를 찾음
        for table in tables:
            if 'Ticker' in table.columns and 'Company' in table.columns:
                nasdaq_table = table
                # 디버깅을 위해 테이블의 일부를 출력
                print("-> 티커 테이블 발견. 상위 5개 행:")
                print(nasdaq_table.head())
                break
            
        # 5. 티커 목록 추출 및 반환
        if nasdaq_table is not None:
            tickers = nasdaq_table['Ticker'].tolist()
            # 리스트 컴프리헨션 > 불필요한 값(NaN, 공백 등)을 제거하고 문자열로만 구성
            tickers = [t for t in tickers if isinstance(t, str) and t.strip()]
            print(f" 티커 리스트 확보 성공. 총 {len(tickers)}개 종목.")
            return tickers
        else:
            print("❌ Ticker 컬럼을 가진 구성 종목 표를 찾지 못했습니다.")
            return []
    except requests.exceptions.HTTPError as e:
        # HTTP 에러 (예: 403 Forbidden, 404 Not Found) 발생 시 처리
        print(f"❌ Http Error (크롤링 차단/URL 오류): {e}")
        return []
    except Exception as e:
        # 기타 모든 예외 상황 처리 (네트워크 문제, 파싱 오류 등)
        print(f"❌ Error >>>>>> 예상치 못한 오류 발생: {e}")
        return []