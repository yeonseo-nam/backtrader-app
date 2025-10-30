from __future__ import absolute_import , division , print_function , unicode_literals
import backtrader as bt

print("Step 1 기본설정")
if __name__ == '__main__':
    cerebro = bt.Cerebro() # Cerebro 객체
    print("Cerebro : ? " , cerebro)
    print('Starting Portfolio Value : %.2f' % cerebro.broker.getvalue())
    # 백테스팅을 수행하는 핵심 함수 (데이터가 없으면 즉시 종료됨)
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())