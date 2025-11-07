import datetime
import backtrader as bt
import pandas as pd
import yfinance as yf
import math
import os

# 커스텀 지표: Donchian Channel
class DonchianChannel(bt.Indicator):
    lines = ('high', 'low',)
    params = (('period', 20),)
    
    def __init__(self):
        self.lines.high = bt.indicators.Highest(self.data.high, period=self.params.period)
        self.lines.low = bt.indicators.Lowest(self.data.low, period=self.params.period)

# 커스텀 지표: OBV SMA
class OBV_SMA(bt.Indicator):
    lines = ('obv_sma',)
    params = (('period', 21),)
    
    def __init__(self):
        self.obv = bt.indicators.OBV(self.data)
        self.lines.obv_sma = bt.indicators.SMA(self.obv, period=self.params.period)

# 전략 클래스
class TurtleStrategy(bt.Strategy):
    params = (
        ('donchian_high_period', 20),
        ('donchian_low_period', 10),
        ('adx_period', 14),
        ('adx_threshold', 25),
        ('ema_period', 50),
        ('atr_period', 20),
        ('atr_multiplier_stop', 2.0),
        ('atr_multiplier_trail', 1.5),
        ('atr_multiplier_pyramid', 1.0),
        ('risk_per_trade', 0.02),  # 계좌의 2% 리스크
        ('max_units', 4),
        ('adx_decline_days', 3),
    )
    
    def log(self, txt, dt=None):
        ''' 로깅 함수 '''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
    
    def __init__(self):
        # 데이터 참조
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # 지표 설정
        # Donchian Channels
        self.donchian_high = DonchianChannel(self.data, period=self.params.donchian_high_period)
        self.donchian_low = DonchianChannel(self.data, period=self.params.donchian_low_period)
        
        # ADX
        self.adx = bt.indicators.ADX(self.data, period=self.params.adx_period)
        
        # EMA50
        self.ema50 = bt.indicators.EMA(self.data.close, period=self.params.ema_period)
        
        # ATR
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        
        # OBV 및 OBV SMA
        self.obv = bt.indicators.OBV(self.data)
        self.obv_sma = OBV_SMA(self.data, period=21)
        
        # MACD
        self.macd = bt.indicators.MACD(self.data)
        
        # 주문 추적
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # 포지션 관리 변수
        self.entry_price = None
        self.initial_stop = None
        self.highest_since_entry = None
        self.units = 0
        self.last_pyramid_price = None
        self.adx_decline_count = 0
        self.last_adx = None
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f, Size: %.0f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm,
                     order.executed.size))
                
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                
                # 첫 진입인 경우
                if self.units == 0:
                    self.entry_price = order.executed.price
                    self.highest_since_entry = order.executed.price
                    self.last_pyramid_price = order.executed.price
                    
                    # 초기 손절 계산
                    atr_value = self.atr[0]
                    if atr_value > 0:
                        self.initial_stop = self.entry_price - (atr_value * self.params.atr_multiplier_stop)
                    else:
                        self.initial_stop = self.entry_price * 0.95  # 기본 5% 손절
                
                self.units += 1
                
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f, Size: %.0f' %
                        (order.executed.price,
                         order.executed.value,
                         order.executed.comm,
                         order.executed.size))
                
                # 포지션 청산 시 변수 초기화
                if not self.position:
                    self.entry_price = None
                    self.initial_stop = None
                    self.highest_since_entry = None
                    self.units = 0
                    self.last_pyramid_price = None
                    self.adx_decline_count = 0
                    self.last_adx = None
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                (trade.pnl, trade.pnlcomm))
    
    def calculate_position_size(self, entry_price, stop_price):
        """포지션 사이즈 계산"""
        if stop_price >= entry_price:
            return 0
        
        stop_distance = entry_price - stop_price
        if stop_distance <= 0:
            return 0
        
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.params.risk_per_trade
        position_size = math.floor(risk_amount / stop_distance)
        
        return max(1, position_size)  # 최소 1주
    
    def check_entry_signal(self):
        """진입 시그널 확인"""
        if len(self.dataclose) < max(self.params.donchian_high_period, self.params.ema_period, self.params.adx_period):
            return False
        
        # 필수 조건
        close_above_donchian = self.dataclose[0] > self.donchian_high.lines.high[0]
        adx_above_threshold = self.adx[0] >= self.params.adx_threshold
        
        if not (close_above_donchian and adx_above_threshold):
            return False
        
        # 권장 조건: EMA50
        close_above_ema = self.dataclose[0] > self.ema50[0]
        
        # 선택 보조 조건: OBV 또는 MACD
        obv_condition = False
        macd_condition = False
        
        if len(self.obv) >= 21:
            obv_condition = self.obv[0] > self.obv_sma.lines.obv_sma[0]
        
        if len(self.macd.macd) > 0:
            macd_condition = self.macd.macd[0] > self.macd.signal[0]
        
        # 최소한 하나의 보조 조건은 만족해야 함 (선택적이지만 권장)
        # 여기서는 필수 조건만으로도 진입 가능하도록 설정
        # 보조 조건이 있으면 더 좋지만 필수는 아님
        
        return True
    
    def check_exit_signal(self):
        """청산 시그널 확인"""
        if not self.position:
            return False
        
        # 즉시 청산 조건 1: DonchianLow(10) 돌파
        if self.dataclose[0] < self.donchian_low.lines.low[0]:
            return True
        
        # 즉시 청산 조건 2: ADX가 3거래일 이상 하락하여 25 미만
        if len(self.adx) > 0:
            current_adx = self.adx[0]
            
            if self.last_adx is not None:
                if current_adx < self.last_adx:
                    self.adx_decline_count += 1
                else:
                    # ADX가 상승하거나 같으면 카운트 리셋
                    self.adx_decline_count = 0
            
            # 3거래일 이상 하락하고 현재 ADX가 25 미만이면 청산
            if self.adx_decline_count >= self.params.adx_decline_days and current_adx < self.params.adx_threshold:
                return True
            
            self.last_adx = current_adx
        else:
            # ADX 데이터가 없으면 초기화
            if self.last_adx is None:
                self.last_adx = self.adx[0] if len(self.adx) > 0 else None
        
        return False
    
    def update_trailing_stop(self):
        """트레일링 스탑 업데이트"""
        if not self.position or self.entry_price is None:
            return None
        
        # 최고가 업데이트
        if self.datahigh[0] > self.highest_since_entry:
            self.highest_since_entry = self.datahigh[0]
        
        # 트레일링 스탑 계산
        atr_value = self.atr[0]
        if atr_value > 0:
            trail_stop = self.highest_since_entry - (atr_value * self.params.atr_multiplier_trail)
            # 트레일링 스탑은 초기 손절보다 낮아지지 않도록
            trail_stop = max(trail_stop, self.initial_stop)
            return trail_stop
        
        return self.initial_stop
    
    def check_pyramid_signal(self):
        """추가 매수(피라미딩) 시그널 확인"""
        if not self.position:
            return False
        
        if self.units >= self.params.max_units:
            return False
        
        if self.last_pyramid_price is None:
            return False
        
        atr_value = self.atr[0]
        if atr_value <= 0:
            return False
        
        # 이전 고점(마지막 피라미딩 가격 또는 진입 가격)에서 +1 * ATR 상승 시 추가 매수
        pyramid_trigger = self.last_pyramid_price + (atr_value * self.params.atr_multiplier_pyramid)
        
        if self.dataclose[0] >= pyramid_trigger:
            return True
        
        return False
    
    def next(self):
        # 주문이 진행 중이면 대기
        if self.order:
            return
        
        # 포지션이 있는 경우
        if self.position:
            # 청산 시그널 확인
            if self.check_exit_signal():
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.close()
                return
            
            # 트레일링 스탑 확인
            trail_stop = self.update_trailing_stop()
            if trail_stop and self.dataclose[0] < trail_stop:
                self.log('TRAILING STOP SELL, %.2f, Stop: %.2f' % (self.dataclose[0], trail_stop))
                self.order = self.close()
                return
            
            # 초기 손절 확인
            if self.initial_stop and self.dataclose[0] < self.initial_stop:
                self.log('STOP LOSS SELL, %.2f, Stop: %.2f' % (self.dataclose[0], self.initial_stop))
                self.order = self.close()
                return
            
            # 피라미딩 확인
            if self.check_pyramid_signal():
                # 추가 매수 사이즈 계산 (첫 진입과 동일한 방식)
                # 모든 유닛은 동일한 stop을 사용하므로 initial_stop 기준으로 계산
                position_size = self.calculate_position_size(self.dataclose[0], self.initial_stop)
                
                if position_size > 0:
                    self.log('PYRAMID BUY CREATE, %.2f, Size: %.0f' % (self.dataclose[0], position_size))
                    self.order = self.buy(size=position_size)
                    # 피라미딩 후 새로운 기준점 설정 (다음 피라미딩을 위한 기준)
                    self.last_pyramid_price = self.dataclose[0]
                    return
        
        # 포지션이 없는 경우 - 진입 시그널 확인
        else:
            if self.check_entry_signal():
                # 진입 가격과 손절 가격 계산
                entry_price = self.dataclose[0]
                atr_value = self.atr[0]
                
                if atr_value > 0:
                    stop_price = entry_price - (atr_value * self.params.atr_multiplier_stop)
                else:
                    stop_price = entry_price * 0.95
                
                # 포지션 사이즈 계산
                position_size = self.calculate_position_size(entry_price, stop_price)
                
                if position_size > 0:
                    self.log('BUY CREATE, %.2f, Size: %.0f, Stop: %.2f' % 
                            (entry_price, position_size, stop_price))
                    self.order = self.buy(size=position_size)


def update_orcl_data_file():
    """orcl-1995-2014.txt 파일을 최신 데이터로 업데이트합니다."""
    # 파일 경로 설정
    modpath = os.path.dirname(os.path.abspath(__file__))
    datapath = os.path.join(modpath, '../datas/yfinance/orcl-1995-2014.txt')
    datapath = os.path.normpath(datapath)
    
    print("="*70)
    print("ORCL 데이터 파일 업데이트 확인 중...")
    print(f"파일 경로: {datapath}")
    
    today = datetime.date.today()
    last_date = None
    
    # 기존 파일이 있으면 마지막 날짜 확인
    if os.path.exists(datapath):
        try:
            df_existing = pd.read_csv(datapath, index_col='Date', parse_dates=True)
            if not df_existing.empty:
                last_date = df_existing.index[-1].date()
                print(f"📅 파일의 마지막 날짜: {last_date}")
                print(f"📅 오늘 날짜: {today}")
                
                # 오늘 날짜와 비교
                if last_date >= today:
                    print(f"✅ 데이터가 최신입니다. (마지막 날짜: {last_date}, 오늘: {today})")
                    print("="*70)
                    return datapath
                
                days_diff = (today - last_date).days
                print(f"🔄 데이터 업데이트가 필요합니다. (차이: {days_diff}일)")
                start_date = last_date + datetime.timedelta(days=1)
            else:
                print("⚠️  기존 데이터 파일이 비어있습니다.")
                print("   전체 데이터를 새로 다운로드합니다...")
                start_date = datetime.date(1995, 1, 1)
        except Exception as e:
            print(f"⚠️  기존 파일 읽기 오류: {e}")
            print("   전체 데이터를 새로 다운로드합니다...")
            start_date = datetime.date(1995, 1, 1)
    else:
        print("⚠️  기존 데이터 파일을 찾을 수 없습니다.")
        print("   전체 데이터를 새로 다운로드합니다...")
        start_date = datetime.date(1995, 1, 1)
    
    # yfinance로 데이터 다운로드
    print(f"📥 ORCL 데이터 다운로드 중... (시작일: {start_date})")
    try:
        ticker = yf.Ticker("ORCL")
        # end_date는 오늘 다음 날로 설정 (오늘까지 포함)
        end_date = today + datetime.timedelta(days=1)
        df_new = ticker.history(start=start_date, end=end_date, auto_adjust=True)
        
        if df_new.empty:
            print("⚠️  새로운 데이터가 없습니다.")
            print("="*70)
            return datapath
        
        print(f"✅ {len(df_new)}개의 새로운 데이터를 받았습니다.")
        
        # 기존 파일이 있으면 추가, 없으면 새로 생성
        if os.path.exists(datapath) and last_date is not None:
            # 기존 데이터 읽기 (이미 위에서 읽었지만, 병합을 위해 다시 읽음)
            df_existing = pd.read_csv(datapath, index_col='Date', parse_dates=True)
            
            # 새 데이터와 병합 (중복 제거)
            df_combined = pd.concat([df_existing, df_new])
            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
            df_combined = df_combined.sort_index()
            
            # CSV로 저장
            df_combined.to_csv(datapath, date_format='%Y-%m-%d')
            print(f"💾 파일 업데이트 완료: {len(df_combined)}개 행 (기존: {len(df_existing)}, 추가: {len(df_new)})")
        else:
            # 새 파일 생성
            df_new.to_csv(datapath, date_format='%Y-%m-%d')
            print(f"💾 새 파일 생성 완료: {len(df_new)}개 행")
        
        print("="*70)
        return datapath
        
    except Exception as e:
        print(f"❌ 데이터 다운로드 오류: {e}")
        print("="*70)
        return datapath

if __name__ == '__main__':
    # ORCL 데이터 파일 업데이트
    orcl_filepath = update_orcl_data_file()
    
    # 백테스트 기간 설정
    fromdate = datetime.datetime(2024, 1, 1)
    todate = datetime.datetime(2025, 11, 4)
    
    # 티커 설정 (예: SPY, 사용자가 원하는 티커로 변경 가능)
    TICKER = "SPY"
    
    print(f"백테스트 시작: {TICKER}")
    print(f"기간: {fromdate.date()} ~ {todate.date()}")
    print("="*70)
    
    # 데이터 가져오기
    ticker = yf.Ticker(TICKER)
    df = ticker.history(start=fromdate, end=todate, auto_adjust=True)
    
    if df.empty:
        print(f"!! 데이터 로드 실패: {TICKER} 데이터를 가져오지 못했습니다. !!")
    else:
        # Cerebro 생성
        cerebro = bt.Cerebro()
        
        # 데이터 추가
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data, name=TICKER)
        
        # 전략 추가
        cerebro.addstrategy(TurtleStrategy)
        
        # 초기 자본 설정
        INITIAL_CASH = 100000.0
        cerebro.broker.setcash(INITIAL_CASH)
        
        # 수수료 설정 (0.1%)
        cerebro.broker.setcommission(commission=0.001)
        
        # 백테스트 실행
        print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
        print("="*70)
        
        results = cerebro.run()
        
        print("="*70)
        print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
        
        # 수익률 계산
        final_value = cerebro.broker.getvalue()
        return_pct = ((final_value - INITIAL_CASH) / INITIAL_CASH) * 100
        print(f'Total Return: {return_pct:.2f}%')
        print("="*70)
        
        # 플로팅 (선택 사항)
        try:
            cerebro.plot(style="candle", barup="red", bardown="blue")
        except Exception as e:
            print(f"플로팅 중 오류 발생: {e}")
            print("matplotlib, backtrader의 최신 버전 등을 확인해 주세요.")

