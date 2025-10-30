from __future__ import absolute_import , division , print_function , unicode_literals
import backtrader as bt
import datetime
import os.path
import sys
'''
Datafeed : 백테스팅 시스템의 가장 근간이 되는 요소이며.
           시뮬레이션 환경을 구성하는 데 필수적인 원천 자료 (과거 시장 데이터)
           (원천자료 = 시가 , 종가 , 고가 , 저가 등 시장 데이터를 담고있음)
'''

'''
DataFeed의 본질적 역할 : 가상 시장 구축
backtrader 는 과거의 특정 시점으로 돌아가 전략을 실행해보는것.(시뮬레이션)
'''


print("Step 3 데이터 피드 추가")
# 샘플 데이터 피드 파일을 찾을 수 있도록 예제 스크립트가 어디에 있는지 찾는다
# 데이터 피드에서 어떤 데이터를 운영할지 날짜/시간 객체를 다룬다
if __name__ == '__main__':
    # Cerebro 객체 생성.   
    cerebro = bt.Cerebro()
    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    print("mod path : " , modpath) # return c:\python\demo-python\backtrader
    datapath = os.path.join(modpath,'../datas/yfinance/orcl-1995-2014.txt')
    print("data path : " , datapath)

    # 데이터 피드
    # YahooFinanceCSVData 클래스는 파일의 내용을 읽어 Parsing(구문분석) 하여
    # backtrader의 lines 구조로 변환하는 역할을 수행한다.
    data = bt.feeds.YahooFinanceCSVData(
        dataname = datapath, # 구문 분석할 파일 이름 혹은 파일과 유사한 객체
        # Do not pass values before this date (시뮬레이션 시작 날짜 이전 날짜의 값 전달x)
        fromdate=datetime.datetime(2000,1,1),
        # Do not pass values after this date  (시뮬레이션 종료 날짜 이후 날짜의 값 전달x)
        todate=datetime.datetime(2000,12,31),
        reverse=False
    )

    # Cerebro 객체에 데이터 피드 추가 , Cerobro 엔진에 데이터 연결
    cerebro.adddata(data) 

    # 현금 설정
    cerebro.broker.setcash(100000.0)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run() # backtrader 실행
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())