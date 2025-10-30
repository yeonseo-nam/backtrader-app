from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt


class TestStrategy(bt.Strategy):
    # strategy logging function
    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        '''
            배열의 index는 시간의 위치만을 나타낸다.
            [0]	    현재 종가 (Today's Close)	next() 메서드가 현재 처리하고 있는 가장 최근의 종가.
            [-1]	어제 종가 (Previous Close)	현재 시점보다 1일 전의 종가.
            [-2]	그저께 종가 (2-Days Ago Close)	현재 시점보다 2일 전의 종가.
        '''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # data[0] 데이터 시리즈의 "닫기" 줄에 대한 참조를 유지
        self.dataclose = self.datas[0].close
        # 인스턴스 초기화
        # 1.보류중인 주문
        self.order = None
        # 2. 매수 주문이 실제로 체결된 가격
        self.buyprice = None
        # 3.체결시 발생한 수수료
        self.buycomm = None

    # 주문이 체결되었을때 (매수/매도) 체결 가격 , 수수료 , 수량등을 기록한다
    def notify_order(self, order):
        # print("Order : " , order.status)
        '''
            Status 1 : Submitted (전략이 브로커에게 주문 제출)
            Status 2 : Accepted  (브로커가 주문 수락 후 체결 대기 상태)
            Status 4 : Completed (주문 체결 완료 , 자산변동 발생)
        '''
        # 1. 제출(Submitted) 및 승인(Accepted) 상태 확인
        # 주문이 브로커에게 전달되었거나(제출), 유효성 검사 후 시장으로 보내진(승인) 상태.
        if order.status in [order.Submitted, order.Accepted]:
            # 아직 현금변동이 없기 때문에 Skip
            return
        # 2. 주문 체결(Completed) 상태 처리(현금이 충분하지 않으면 주문체결 x)
        if order.status in [order.Completed]:
            if order.isbuy():
                # 체결정보 상세기록
                # Cost : 순수 거래 금액 (체결 가격 * 수량). 수수료는 제외된 값
                self.log(
                    '매수 체결, 가격: %.2f, 비용: %.2f, 수수료: %.2f' %
                    (order.executed.price,
                    order.executed.value,
                    order.executed.comm))
                # 수익 계산을 위한 정보 저장
                self.buyprice = order.executed.price # 1주당 매수 가격 저장
                self.buycomm = order.executed.comm   # 총 수수료 금액
            else: # 판매인경우
                self.log(
                    '매도 체결, 가격: %.2f, 수입: %.2f, 수수료: %.2f' %
                    (order.executed.price,
                    order.executed.value,
                    order.executed.comm))
            # 매수/매도 체결된 바(Bar) 인덱스 기록 (5일 보유기간 계산을 위함)
            self.bar_executed = len(self)
   
        elif order.status in [order.Canceled , order.Margin , order.Rejected]:
            self.log('Order Canceled / Margin / Rejected')
            
        self.order = None

    # 거래(Trade)가 완전히 청산(매수 + 매도)되어 종료되었을 때 호출
    # 상세기록 출력
    def notify_trade(self , trade):
        if not trade.isclosed:
            return
        # 총 손익 (Gross) 및 순 손익 (Net, 수수료 포함) 기록
        self.log('거래 수익 발생, 총 이익: %.2f, 순 이익: %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        # 참조에서 시리즈의 종가를 간단히 기록합니다.
        self.log('종가: , %.2f' % self.dataclose[0])

        # 주문중복방지 : 현재 진행 중인 미결 주문이 있다면 Skip
        if self.order:
            return
        
        # 현재 보유주식이 없는 경우 (매수 기회)
        if not self.position:
            # 매수조건
            # 현재 종가가 이전 종가보다 낮은경우 -> 어제보다 하락하였는가?
            if self.dataclose[0] < self.dataclose[-1]:
                # 이전 종가가 연속 하락 종가인경우 -> 이틀연속 하락하였는가?
                if self.dataclose[-1] < self.dataclose[-2]:
                    self.log("매수 주문 생성: %.2f" % self.dataclose[0])
                    # 매수 주문 생성 후 주문 객체를 self.order에 저장(추적용)
                    self.order = self.buy()
        # 현재 보유주식이 있는경우 (매수 기회)
        else:
            # 현재 시점 (len(self) > 양봉/음봉(bar)이 매수 시점 + 5보다 크거나 같은 경우 를 확인 
            # 매수한 시점(self.bar_executed)
            # 매도 포지션	len(self)	현재 시점 (바 번호). 매도(청산) 주문이 생성되는 시점을 기록.
             #매수 포지션	self.bar_executed	과거 시점 (바 번호). 매수(진입) 포지션이 체결된 시점을 기록.

           # 매수 체결 후 5일이 지났을 경우 매도
            if len(self) >= (self.bar_executed + 5): 
                #print('매도 포지션 : ' ,len(self) , ' / ' , '매수포지션 : ', self.bar_executed )
                self.log('매도 주문 생성: %.2f' % self.dataclose[0])
                # 매도 주문 생성 후 주문 객체를 self.order에 저장(추적용)
                self.order = self.sell()

if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(TestStrategy)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, '../datas/yfinance/orcl-1995-2014.txt')

    # Create a Data Feed
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(2000, 1, 1),
        # Do not pass values before this date
        todate=datetime.datetime(2000, 12, 31),
        # Do not pass values after this date
        reverse=False)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # 초기 현금 설정 값 세팅
    cerebro.broker.setcash(100000.0)
    
    # 수수료 가격(0.1%) 
    cerebro.broker.setcommission(commission=0.001)

    # getvalue() 시뮬레이션 시장의 주가 변동을 실시간으로 반영
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue()) 
    # Starting Portfolio 는 초기 현금 설정 값
    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    # Final Portfoli value 계산식 : 최종 현금 잔고 + ( 보유 주식 수 x 현재 시장 가격) - 누적 거래 수수료
