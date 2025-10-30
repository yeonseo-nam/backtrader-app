from nasdaq_data import get_nasdaq_100_tickers as nasdaq_tickers
from yfinance_data import find_50_day_highs
import pandas as pd

if __name__ == "__main__":
     # 1. 티커 리스트 가져오기 (nasdaq_data 모듈의 함수 사용)
    tickers = nasdaq_tickers()

    if tickers is not None:
        # 2. 50일 신고가 종목 찾기
        result_list = find_50_day_highs(tickers)
        print("\n" + "="*70)
        print("    ⭐ 나스닥 100 종목 중 50일 신고가 기록 종목 ⭐")
        print("="*70)
        if result_list:
            print(f"🎉 총 {len(result_list)}개 종목:")
               # 리스트를 DataFrame으로 변환하여 표 형태로 깔끔하게 출력
            result_df = pd.DataFrame(result_list)
            # 주가를 보기 쉽게 소수점 두 자리로 포매팅
            result_df['Current_Price'] = result_df['Current_Price'].round(2) 
            print(result_df.to_string(index=False)) # 인덱스 없이 출력

        else:
            print("🔍 현재 기준으로 50일 신고가를 기록한 종목은 없습니다.")
        print("="*60)
    else:
        print("❗ 티커 리스트를 가져오는 데 실패하여 분석을 진행할 수 없습니다.")
