# indicators - 지표
# 종가가 평균보다 높으면 AtMarket을 구매한다.
# 시장에 있는 경우 마감가가 평균보다 작으면 매도

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
# Import the backtrader platform
import backtrader as bt

class TestStrategy(bt.Strategy):
    # 이동평균선 파라미터 설정(15일)
    params = (('maperiod', 15),)
    
    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # 인스턴스 초기화
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # ----------------------------------------------------------------------------------
        # [⭐ SMA 지표 핵심] Simple Moving Average 지표 생성
        # ----------------------------------------------------------------------------------
        # SMA는 가격 데이터의 '노이즈(Noise)'를 줄여 추세 방향을 시각화하는 지연 지표.
        # 현재는 15일 이동평균선 전체
        self.sma = bt.indicators.SimpleMovingAverage(
            # SMA 계산 대상 데이터 지정 (기본은 종가)
            self.datas[0], 
            # SMA 계산에 사용할 기간 설정 (여기서는 15일)
            period=self.params.maperiod)
    
    def notify_order(self,order):
        
        # 주문정보가 브로커에게 제출했거나 시장에 승인중인 경우
        if order.status in [order.Submitted, order.Accepted]:
            # 현금변동이 없으므로 Skip (로그기록x)
            return
        
        # 주문이 체결된경우
        if order.status in [order.Completed]:
            
            # 매수하였을경우 상세기록을 출력한다
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
                # 매수 정보
                self.buyprice = order.executed.price # 금액
                self.buycomm = order.executed.comm   # 수수료
            # 매도하였을경우 상세기록을 출력한다.
            else :
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
            # 매도포인트 정보 저장
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        self.order = None # 주문정보 초기화
        
    # 거래정보가 완전히 청산됐을경우 해당 함수를 호출.
    # 매수 + 매도
    def notify_trade(self , trade):
        if not trade.isclosed:
            return
        # 총 손익 (Gross) 및 순 손익 (Net, 수수료 포함) 기록
        self.log('거래 수익 발생, 총 이익: %.2f, 순 이익: %.2f' %
                 (trade.pnl, trade.pnlcomm))
        # self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
        #          (trade.pnl, trade.pnlcomm))
    
    # 전략의 핵심 로직 (새로운 데이터 바(Bar)가 들어올 때마다 실행)
    def next(self):
        # 현재 종가 정보를 출력한다
        self.log('Close, %.2f' % self.dataclose[0])
            
        # 중복주문방지
        if self.order:
            return
        
        # ------------------------------------------------------------------------------------------------
        # [⭐ SMA 전략 핵심] 종가와 이동평균선(SMA)의 관계를 이용한 크로스오버 전략
        # ------------------------------------------------------------------------------------------------
        
        # 현재 보유 주식이 없는경우 매수 로직을 실행한다.        
        if not self.position:
            # 매수 진입: 종가(dataclose[0])가 15일 평균선(self.sma[0])보다 높으면 매수
            # -> 단기적으로 추세가 '강세'로 전환되어 상승 추세에 진입했다고 판단
            if self.dataclose[0] > self.sma[0]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
        # 매도 청산 : 현재 보유 주식이 있는 경우 매도 로직을 실행한다
        else:
            # 매도 청산: 종가(dataclose[0])가 15일 평균선(self.sma[0])보다 낮으면 매도
            # -> 단기적으로 추세가 '약세'로 전환되어 추세가 무너졌다고 판단, 포지션 청산
            if self.dataclose[0] < self.sma[0]:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()

if __name__ == '__main__':
    
    # Cerebro 객체 생성
    cerebro = bt.Cerebro()
    
    # Strategy -> 전략 실행
    cerebro.addstrategy(TestStrategy)
    
    # 분석대상 파일 경로 설정
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, '../datas/yfinance/orcl-1995-2014.txt')
    
    # DataFeed 설정
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(2000, 1, 1),
        # Do not pass values before this date
        todate=datetime.datetime(2000, 12, 31),
        # Do not pass values after this date
        reverse=False
    )
    # DataFeed 추가
    cerebro.adddata(data)
    
    # 초기 금액설정
    cerebro.broker.setcash(1000.0)
    
    # FixedSize : 매수 주문 발생 시 몇 주를 살지 결정
    # stake : 10주씩 강제 구매 
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # 수수료설정
    cerebro.broker.setcommission(commission=0.0)
    
    # 초기 포트폴리오 금액 출력
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    # Cerebro 엔진 실행
    cerebro.run()
    
    # Cerebro 실행 후 포트폴리오 금액 출력
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    
    
    