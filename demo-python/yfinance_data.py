# main.py 파일

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# nasdeq_data.py 파일에서 티커 추출 함수를 임포트하고,
# 요청하신 'nasdeqTickerList'라는 이름으로 사용합니다.
from nasdaq_data import get_nasdaq_100_tickers as nasdeqTickerList 

# ----------------------------------------------------------------------
# 2단계 & 3단계: 주가 데이터 다운로드 및 50일 신고가 분석 함수
# ----------------------------------------------------------------------

def find_50_day_highs(tickers):
    """
    주어진 티커 리스트에 대해 yfinance를 사용하여 50일 신고가 종목을 찾기
    """
    WINDOW = 50 # 50 거래일 기준
    
    # 50거래일 데이터를 안전하게 확보하기 위해 넉넉히 6개월(약 180일)의 데이터 요청
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180) 
    
    high_50_day_stocks = []
    
    print("\n👉 2단계: 주가 데이터를 다운로드하고 50일 신고가를 분석하는 중...")
    
    # 티커 리스트가 많은 관계로 진행 상황을 알 수 있도록 간단한 카운터를 추가.
    total_tickers = len(tickers)
    print("티커 리스트 : " , total_tickers)

    for i, ticker in enumerate(tickers):
        # 10개 종목마다 진행 상황을 출력 (옵션)
        if (i + 1) % 10 == 0 or (i + 1) == total_tickers:
            print(f"   -> {i + 1}/{total_tickers} 종목 처리 중...")
            
        try:
            # yfinance로 일봉(interval="1d") 데이터 다운로드 (progress=False로 깔끔하게 출력)
            data = yf.download(ticker, start=start_date, end=end_date, interval="1d", progress=False)
            
            # 데이터가 50일치 이상 존재하는지 확인

            # yfinance 다운로드 시 MultiIndex가 생성되는 것을 방지하거나, 
            # MultiIndex라면 첫 번째 레벨을 제거하여 컬럼명을 단일화합니다.
            if isinstance(data.columns, pd.MultiIndex):
                # 멀티 인덱스 컬럼을 가진 경우, 레벨 1(티커 심볼)을 제거하고 레벨 0(High, Low 등)만 남김.
                data.columns = data.columns.droplevel(1)
                
            ticker_info = yf.Ticker(ticker)

            if len(data) >= WINDOW:
                # 50일 이동 최고가 계산: 'High' 컬럼에 대해 50일 롤링 최댓값 적용
                data['50D_High'] = data['High'].rolling(window=WINDOW).max()

                # 가장 최근 거래일의 데이터 추출
                latest_data = data.iloc[-1]
                
                # 50일 신고가 조건: 최근 장중 최고가('High')가 지난 50일간의 최고가와 일치하는지 확인
                if latest_data['High'] == latest_data['50D_High']:
                    high_50_day_stocks.append({
                        'Ticker': ticker,
                        # info 딕셔너리에서 'shortName' 또는 'longName' 사용
                        'Name': ticker_info.info.get('shortName', 'N/A'), 
                        'Current_Price': latest_data['Close'] 
                    })

        except Exception:
            # 다운로드 또는 데이터 처리 오류 시 해당 종목은 건너뜁니다.
            continue
        
    print("✅ 50일 신고가 분석 완료.")
    return high_50_day_stocks