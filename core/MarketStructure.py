from AlgorithmImports import *
class MarketStructure:
    def __init__(self, params, tf):
        self.tf = tf
        self.params = params
        self.symbol = params["symbol"]
        self.market_structure_bars = params["MARKET_STRUCTURE_BARS"]
        self.market_structure = []
        self.resolution = timedelta(minutes=tf)
        self.bars = RollingWindow[QuoteBar](50000)

    def Initialize(self, algorithm):
        self.algorithm = algorithm
        consolidator = algorithm.Consolidate(self.symbol, self.resolution, self.OnMarketStructureBar)

        # Process historical data
        history = self.algorithm.History(QuoteBar, self.symbol, 5000, Resolution.Minute)
        count = 0
        
        for time, row in history.iterrows():
            consolidator.Update(QuoteBar(
            time = time[1].to_pydatetime(),
            symbol = self.symbol,
            bid = Bar(row['bidopen'], row['bidhigh'], row['bidlow'], row['bidclose']),
            lastBidSize=0,
            ask = Bar(row['askopen'], row['askhigh'], row['asklow'], row['askclose']),
            lastAskSize=0
            ))
            count += 1


    def GetPivotHigh(self):
        if self.bars.count < 2 * self.market_structure_bars + 1:
            return None  # Not enough bars to determine a pivot high

        for i in range(self.market_structure_bars, self.bars.count - self.market_structure_bars):
            high = self.bars[i].high
            is_pivot = True
            for j in range(1, self.market_structure_bars + 1):
                if self.bars[i + j].high > high:
                    is_pivot = False
                    break
            for j in range(0, i):
                if self.bars[j].high > high:
                    is_pivot = False
                    break
            if is_pivot:
                return high

        return None

    def GetPivotLow(self):
        if self.bars.count < 2 * self.market_structure_bars + 1:
            return None  # Not enough bars to determine a pivot low

        for i in range(self.market_structure_bars, self.bars.count - self.market_structure_bars):
            low = self.bars[i].low
            is_pivot = True
            for j in range(1, self.market_structure_bars + 1):
                if self.bars[i + j].low < low:
                    is_pivot = False
                    break
            for j in range(0, i):
                if self.bars[j].low < low:
                    is_pivot = False
                    break
            if is_pivot:
                return low

        return None

    def OnMarketStructureBar(self, bar):
        pivot_high = self.GetPivotHigh()
        pivot_low = self.GetPivotLow()
        if pivot_high is not None and bar.high > pivot_high:
            self.market_structure.append("uptrend")
        if pivot_low is not None and bar.low < pivot_low:
            self.market_structure.append("downtrend")
        self.bars.add(bar)

    def GetLatestMarketStructure(self):
        if self.market_structure:
            return self.market_structure[-1]
        return None