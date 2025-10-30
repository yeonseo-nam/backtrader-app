from __future__ import absolute_import , division , print_function , unicode_literals
import backtrader as bt
# 현금설정
print("Step 2 현금설정")

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100000.0) # 1만 달러
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())