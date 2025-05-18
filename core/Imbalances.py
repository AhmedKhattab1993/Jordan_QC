
from AlgorithmImports import *
class Imbalances:
    def __init__(self, params):
        self.symbol = params["symbol"]
        self.imbalances_tf = params["LOW_TF"]
        self.gaps_imbalances_factor = params["GAPS_IMBALANCES_FACTOR"]
        self.gaps_imbalances_avg_n = params["GAPS_IMBALANCES_AVG_N"]
        self.bar_body_imbalances_factor = params["BAR_BODY_IMBALANCES_FACTOR"]
        self.bar_body_imbalances_n = params["BAR_BODY_IMBALANCES_N"]
        self.multiple_bars_imbalances_n = params["MULTIPLE_BARS_IMBALANCES_N"]
        self.bars_wicks_imbalances_n = params["BARS_WICKS_IMBALANCES_N"]
        self.bars_wicks_imbalances_factor = params["BARS_WICKS_IMBALANCES_FACTOR"]
        self.imbalances_fill_pct = params["IMBALANCES_FILL_PCT"]
        self.bars = []
        self.gaps_imbalances = []
        self.body_imbalances = []
        self.multiple_bars_imbalances = []
        self.wick_imbalances = []
        self.enable_gaps = params["ENABLE_GAPS"]
        self.enable_body = params["ENABLE_BODY"]
        self.enable_multiple = params["ENABLE_MULTIPLE"]
        self.enable_wick = params["ENABLE_WICK"]
    def Initialize(self, algorithm):
        self.resolution = timedelta(minutes=self.imbalances_tf)
        self.algorithm = algorithm
        algorithm.Consolidate(self.symbol, self.resolution, self.OnImbalancesBar)

    def OnImbalancesBar(self, bar):
        if self.enable_gaps:
            self.detect_gaps_imbalances(bar)
        if self.enable_body:
            self.detect_body_imbalances(bar)
        if self.enable_multiple:
            self.detect_multiple_bars_imbalances(bar)
        if self.enable_wick:
            self.detect_wick_imbalances(bar)
        self.bars.append(bar)
        self.gaps_imbalances = self.check_valid(bar, self.gaps_imbalances)
        self.body_imbalances = self.check_valid(bar, self.body_imbalances)
        self.multiple_bars_imbalances = self.check_valid(bar, self.multiple_bars_imbalances)
        self.wick_imbalances = self.check_valid(bar, self.wick_imbalances)

    def detect_gaps_imbalances(self,bar):
        if len(self.bars) > 0:
            previous_close = self.bars[-1].Close
            gap = abs(previous_close - bar.Open)
            if len(self.bars) >= self.gaps_imbalances_avg_n:
                last_n_bars = self.bars[-self.gaps_imbalances_avg_n:]
                gaps = [abs(last_n_bars[i].Close - last_n_bars[i+1].Open) for i in range(len(last_n_bars) - 1)]
                average_gap = sum(gaps) / len(gaps)
                if gap > average_gap * self.gaps_imbalances_factor:
                    direction = self.direction(previous_close,bar.Open)
                    self.gaps_imbalances.append((bar.time, previous_close, bar.Open,direction))

    def detect_body_imbalances(self,bar):
        if len(self.bars) > 0:
            body = abs(self.bars[-1].Close - self.bars[-1].Open)
            if len(self.bars) >= self.bar_body_imbalances_n:
                last_n_bars = self.bars[-self.bar_body_imbalances_n+1:]
                bodies = [abs(last_n_bars[i].Close - last_n_bars[i].Open) for i in range(len(last_n_bars))]
                average_body = sum(bodies) / len(bodies)
                if body > average_body * self.bar_body_imbalances_factor:
                    if bar.Close > bar.Open:
                        self.body_imbalances.append((self.bars[-1].time, self.bars[-2].High, bar.Low, self.direction(self.bars[-2].High,bar.Low)))
                    else:
                        self.body_imbalances.append((self.bars[-1].time, self.bars[-2].Low, bar.High, self.direction(self.bars[-2].Low,bar.High)))

    def detect_multiple_bars_imbalances(self, bar):
        if len(self.bars) > self.multiple_bars_imbalances_n:
            consecutive_bars = self.bars[-self.multiple_bars_imbalances_n:]
            if (all(b.Close > b.Open for b in consecutive_bars) or all(b.Close < b.Open for b in consecutive_bars)):
                imbalance_start = self.bars[-self.multiple_bars_imbalances_n - 1].Open
                imbalance_end = bar.Close
                self.multiple_bars_imbalances.append((bar.Time, imbalance_start, imbalance_end, self.direction(imbalance_start, imbalance_end)))

    def detect_wick_imbalances(self, bar):
        if len(self.bars) >= self.bars_wicks_imbalances_n + 2:
            wick_up_distances = [abs(self.bars[-i - 2].High - self.bars[-i].Low) for i in range(1, self.bars_wicks_imbalances_n + 1)]
            wick_down_distances = [abs(self.bars[-i - 2].Low - self.bars[-i].High) for i in range(1, self.bars_wicks_imbalances_n + 1)]
            avg_wick_up = sum(wick_up_distances) / len(wick_up_distances)
            avg_wick_down = sum(wick_down_distances) / len(wick_down_distances)
            last_wick_up = abs(self.bars[-2].High - bar.Low)
            last_wick_down = abs(self.bars[-2].Low - bar.High)
            if last_wick_up > (avg_wick_up * self.bars_wicks_imbalances_factor) and bar.Low > self.bars[-2].High:
                self.wick_imbalances.append((bar.Time, self.bars[-2].High, bar.Low, self.direction(self.bars[-2].High, bar.Low)))
            if last_wick_down > (avg_wick_down * self.bars_wicks_imbalances_factor) and bar.High < self.bars[-2].Low:
                self.wick_imbalances.append((bar.Time, self.bars[-2].Low, bar.High, self.direction(self.bars[-2].Low, bar.High)))

    def direction(self, startRange, endRange):
        if startRange > endRange:
            return "above"
        else:
            return "below"

    def check_valid(self, bar, imbalances):
        if len(imbalances) > 0:
            for imbalance in imbalances:
                if imbalance[0] == bar.Time:
                    continue

                max_range = max(imbalance[1], imbalance[2])
                min_range = min(imbalance[1], imbalance[2])
                fill_percentage_price = min_range + ((max_range - min_range) * self.imbalances_fill_pct)

                crossed_pct = (bar.High > fill_percentage_price if imbalance[1] > imbalance[2] else bar.Low < fill_percentage_price)

                crossed_range = (bar.High > max_range or bar.Low < min_range)

                if crossed_pct and crossed_range:
                    imbalances.remove(imbalance)

        return imbalances

    def find_nearest_imbalances(self, price):
        nearest_above = None
        nearest_below = None
        min_above_diff = float('inf')
        min_below_diff = float('inf')

        for imbalance in self.gaps_imbalances + self.body_imbalances + self.multiple_bars_imbalances + self.wick_imbalances:
            if imbalance[3] == "above":
                diff = imbalance[1] - price
                if diff > 0 and diff < min_above_diff:
                    min_above_diff = diff
                    nearest_above = imbalance
            else:
                diff = price - imbalance[2]
                if diff > 0 and diff < min_below_diff:
                    min_below_diff = diff
                    nearest_below = imbalance
        return nearest_above, nearest_below
