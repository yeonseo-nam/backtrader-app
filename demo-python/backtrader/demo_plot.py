import datetime
import backtrader as bt
import pandas as pd
import yfinance as yf # yfinance를 yf로 import 합니다.

# Create a Stratey
# Strategy 클래스를 상속받아서 거래로직을 정의
class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        # 현재 라인(날짜, index 0)의 종가(close)를 self.dataclose에 저장
        self.dataclose = self.datas[0].close
        # 주문(Order)의 상태를 추적하기 위한 레퍼런스
        self.order = None

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])
        
        # 테스트를 위해 간단한 매매 로직 추가: 포지션이 없으면 매수
        if not self.position:
            # 주가 기록 (로그)
            self.log('BUY CREATE, %.2f' % self.dataclose[0])
            # 매수 주문 실행
            self.order = self.buy()

# 주의: yf.Ticker().history(auto_adjust=True) 사용 시 수정 종가 보정 함수는 필요 없습니다.
# Adj Close가 Close 컬럼에 반영되어 반환됩니다.

if __name__ == '__main__':
    # 2. 테스트 구간 정하기
    fromdate = datetime.datetime(2021, 1, 1)
    todate = datetime.datetime(2021, 7, 6)

    # 1. 데이터 가져오기: yf.Ticker().history() 사용 (컬럼 오류 방지 및 데이터 안정성 확보)
    # auto_adjust=True: 주가 데이터가 분할 및 배당에 대해 자동 조정되도록 설정 (Adj Close 반영)
    ticker = yf.Ticker("SPY")
    df_spy = ticker.history(start=fromdate, end=todate, auto_adjust=True)
    
    # 데이터가 비어 있는지 확인
    if df_spy.empty:
        print("!! 데이터 로드 실패: 지정된 기간 동안 SPY 데이터를 가져오지 못했습니다. !!")
    else:
        # 3. 테스트 agent 생성
        cerebro = bt.Cerebro()
        
        # bt.feeds.PandasData에 데이터프레임을 전달
        # yfinance의 history() 메서드는 backtrader가 요구하는 컬럼명(Open, High, Low, Close, Volume)을 가집니다.
        data_spy = bt.feeds.PandasData(dataname=df_spy)
        cerebro.adddata(data_spy, name="SPY")

        # 4. Add strategy
        cerebro.addstrategy(TestStrategy)

        # 5. Set our desired cash start
        cerebro.broker.setcash(10000)
        
        # 6. (선택 사항) 커미션 설정
        cerebro.broker.setcommission(commission=0.001) # 0.1% 수수료

        # 7. 백테스트 시작
        print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
        results = cerebro.run()
        print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
        
        # 8. 플로팅
        try:
             cerebro.plot(style="candle", barup="red", bardown="blue")
        except Exception as e:
            print(f"플로팅 중 오류 발생: {e}")
            print("matplotlib, backtrader의 최신 버전 등을 확인해 주세요.")