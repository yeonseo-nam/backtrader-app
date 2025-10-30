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
            [0]	    현재 종가 (Today's Close)	next() 메서드가 현재 처리하고 있는 가장 최근의 종가입니다.
            [-1]	어제 종가 (Previous Close)	현재 시점보다 1일 전의 종가입니다.
            [-2]	그저께 종가 (2-Days Ago Close)	현재 시점보다 2일 전의 종가입니다.
        '''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        # data[0] 데이터 시리즈의 "닫기" 줄에 대한 참조를 유지하세요.
        self.dataclose = self.datas[0].close

    def next(self):
        # Simply log the closing price of the series from the reference
        # 참조에서 시리즈의 종가를 간단히 기록합니다.
        self.log('Close, %.2f' % self.dataclose[0])
        
        # 현재 종가가 이전 종가보다 낮은경우 -> 어제보다 하락하였는가?
        if self.dataclose[0] < self.dataclose[-1]:
            # 이전 종가가 연속 하락 종가인경우 -> 이틀연속 하락하였는가?
            if self.dataclose[-1] < self.dataclose[-2]:
                self.log("Buy, %.2f" % self.dataclose[0])
                self.buy()



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

    # getvalue() 시뮬레이션 시장의 주가 변동을 실시간으로 반영
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue()) 
    # Starting Portfolio 는 초기 현금 설정 값
    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
    # Final Portfoli value 계산식 : 최종 현금 잔고 + ( 보유 주식 수 x 현재 시장 가격) - 누적 거래 수수료
