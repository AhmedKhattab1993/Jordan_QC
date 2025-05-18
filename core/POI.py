from AlgorithmImports import *
import numpy as np
import datetime

class POI:
    def __init__(self, params):
        self.params = params
        self.symbol = params["symbol"]
        self.timeFrame = params["LOW_TF"]
        self.g1Min = params["POINT_OF_INTEREST_G1_MIN"]
        self.g1Max = params["POINT_OF_INTEREST_G1_MAX"]
        self.g2Min = params["POINT_OF_INTEREST_G2_MIN"]
        self.g2Max = params["POINT_OF_INTEREST_G2_MAX"]
        self.POIMultiple = int(params["POINT_OF_INTEREST_MULTIPLE"])
        self.pivotsBars = params["POINT_OF_INTEREST_PIVOTS_BARS"]
        self.poi_valid = []

    def Initialize(self, algorithm):
        self.algorithm = algorithm
        self.bars = RollingWindow[QuoteBar](50000)
        self.resolution = timedelta(minutes=self.timeFrame)
        consolidator = algorithm.Consolidate(self.symbol, self.resolution, self.OnDataConsolidated)

        # Process historical data
        history = self.algorithm.History(QuoteBar, self.symbol, 5000, Resolution.Minute)
        count = 0
        for time, row in history.iterrows():
            consolidator.Update(QuoteBar(
            time = time[1].to_pydatetime(),
            symbol = self.symbol,
            bid = Bar(row['open'], row['high'], row['low'], row['close']),
            lastBidSize=0,
            ask = Bar(row['open'], row['high'], row['low'], row['close']),
            lastAskSize=0
            ))
            count += 1

    def OnDataConsolidated(self, bar):
        self.bars.add(bar)
        self.ValidatePOIs(bar)
        if self.bars.count > max(self.g1Max + self.g2Max + 2, self.pivotsBars*2):
            self.ProcessBars()

    def GetPivotHigh(self, index):
        highest = 0.0
        for i in range(index, index+self.pivotsBars):
            highest = max(highest, self.bars[i].high)
        return highest

    def GetPivotLow(self, index):
        lowest = 9999.0
        for i in range(index, index+self.pivotsBars):
            lowest = min(lowest, self.bars[i].low)
        return lowest

    def ProcessBars(self):
        for i in range(self.g2Max+1):
            highest_g2 = 0
            lowest_g2 = 99999
            highest_open = 0.0
            lowest_open = 99999
            r_g2 = 0
            for j in range(i+1):
                highest_g2 = max(highest_g2, self.bars[j].High)
                lowest_g2 = min(lowest_g2, self.bars[j].Low)
                r_g2 = highest_g2 - lowest_g2
                if self.bars[i].Close > self.bars[i].Open:
                    highest_open = max(highest_open, self.bars[i].Open)
                if self.bars[i].Close < self.bars[i].Open:
                    lowest_open = min(lowest_open, self.bars[i].Open)

            if (highest_g2 == self.bars[i].High and lowest_g2 == self.bars[0].low) or (highest_g2 == self.bars[0].High and lowest_g2 == self.bars[i].low):
                highest_g1 = 0.0
                lowest_g1 = 99999
                count_g1 = 0.0
                for k in range(1, self.g1Max+1):
                    count_g1 = count_g1 + 1
                    highest_g1 = max(highest_g1 , self.bars[i + k].high)
                    lowest_g1 = min(lowest_g1 , self.bars[i + k].low)
                    if self.bars[i+k].Close > self.bars[i+k].Open:
                        highest_open = max(highest_open, self.bars[i+k].Open)
                    if self.bars[i+k].Close < self.bars[i+k].Open:
                        lowest_open = min(lowest_open, self.bars[i+k].Open)
                    if count_g1 < self.g1Min:
                        continue
                    r_g1 = highest_g1 - lowest_g1
                    if r_g1 > 0:
                        if (r_g2 / r_g1) >  self.POIMultiple:
                            if self.bars[0].close < lowest_g1 and self.bars[i+1].close > self.bars[i+1].open and self.bars[i+1].open == highest_open:
                                self.poi_valid.append({'type': "resistance", 'pivot': self.GetPivotHigh(i+1) ,'price': self.bars[i+1].Open, 'time': self.bars[i+1].Time})
                            if self.bars[0].close > highest_g1 and self.bars[i+1].close < self.bars[i+1].open and self.bars[i+1].open == lowest_open:
                                self.poi_valid.append({'type': "support", 'pivot': self.GetPivotLow(i+1),  'price': self.bars[i+1].Open, 'time': self.bars[i+1].Time})

    def ValidatePOIs(self, bar):
        self.poi_valid = [poi for poi in self.poi_valid if
                          (poi['type'] == 'support' and bar.low > poi['price']) or
                          (poi['type'] == 'resistance' and bar.high < poi['price'])]

    def GetNearestPOIs(self):
        last_poi_support = None
        last_poi_resistance = None
        for poi in reversed(self.poi_valid):
            if poi['type'] == 'support':
                last_poi_support = poi
                break
        for poi in reversed(self.poi_valid):
            if poi['type'] == 'resistance':
                last_poi_resistance = poi
                break
        return last_poi_support, last_poi_resistance