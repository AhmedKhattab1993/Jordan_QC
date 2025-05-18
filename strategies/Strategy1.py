from AlgorithmImports import *
from core.MarketStructure import MarketStructure
from core.POI import POI
from core.Imbalances import Imbalances
from datetime import datetime, time, timedelta

class Strategy1:
    def __init__(self, params):
        self.params = params
        self.symbol = params["symbol"]
        self.low_tf = params["LOW_TF"]
        self.high_tf = params["HIGH_TF"]
        self.risk_reward_target_1 = params["RISK_REWARD_TARGET_1"]
        self.risk_reward_target_2 = params["RISK_REWARD_TARGET_2"]
        self.account_risk_pct = params["ACCOUNT_RISK_PCT"]
        self.stoploss_update_pips = params["STOPLOSS_UPDATE_PIPS"]
        self.enable_imbalances = params["ENABLE_IMBALANCES"]
        self.enable_stoploss_update = params["ENABLE_STOPLOSS_UPDATE"]
        self.enable_multiple_positions = params["ENABLE_MULTIPLE_POSITIONS"]
        self.entry_buffer_pips = params['ENTRY_BUFFER_PIPS']
        self.market_structure_algo = None
        self.poi_algo = None
        self.order_tag_id = 1
        self.open_trades = []
        self.closed_trades = []
        self.pending_order = None
        self.pip_value = 0.0001

    def Initialize(self, algorithm):
        self.resolution = timedelta(minutes=self.low_tf)
        self.market_structure_algo_low = MarketStructure(self.params, self.low_tf)
        self.market_structure_algo_low.Initialize(algorithm)
        self.market_structure_algo_high = MarketStructure(self.params, self.high_tf)
        self.market_structure_algo_high.Initialize(algorithm)
        self.poi_algo = POI(self.params)
        self.poi_algo.Initialize(algorithm)
        self.imbalances = Imbalances(self.params)
        self.imbalances.Initialize(algorithm)
        self.algorithm = algorithm
        self.algorithm.SetWarmUp(timedelta(minutes=self.low_tf * 2))
        self.algorithm.set_time_zone(TimeZones.NEW_YORK)
        algorithm.Consolidate(self.symbol, self.resolution, self.OnDataConsolidated)

        consolidator = algorithm.Consolidate(self.symbol, self.resolution, self.OnDataConsolidated)

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

    def GetDayOccurrenceInMonth(self):
        current_date = self.algorithm.Time.date()
        day_of_week = current_date.weekday()  # Monday is 0 and Sunday is 6
        first_day_of_month = current_date.replace(day=1)
        day_count = 0

        for day in range(1, current_date.day + 1):
            if first_day_of_month.weekday() == day_of_week:
                day_count += 1
            first_day_of_month += timedelta(days=1)

        return day_of_week, day_count

    def IsLastOccurrenceInMonth(self):
        current_date = self.algorithm.Time.date()
        day_of_week = current_date.weekday()  # Monday is 0 and Sunday is 6
        days_in_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        last_day_of_month = days_in_month.day

        # Find the last occurrence of the current day of the week in this month
        last_occurrence = last_day_of_month
        while last_occurrence > current_date.day:
            if current_date.replace(day=last_occurrence).weekday() == day_of_week:
                break
            last_occurrence -= 1

        return current_date.day == last_occurrence

    def OnDataConsolidated(self, data):
        if self.algorithm.IsWarmingUp:
            return
        current_price = self.algorithm.Securities[self.symbol].Price
        if self.pending_order is not None and not self.IsEntryPriceWithinImbalance(current_price, self.pending_order['entry_price']) and self.enable_imbalances:
            self.algorithm.Transactions.CancelOrder(self.pending_order['order_id'], f"Order Tag #{self.pending_order['order_tag_id']}: Pending Order Cancelled (Outside Imbalance Range)")
            self.pending_order = None

        latest_market_structure = self.market_structure_algo_low.GetLatestMarketStructure()
        last_poi_support, last_poi_resistance = self.poi_algo.GetNearestPOIs()
        if (self.pending_order is not None and self.pending_order['type'] == 'long') and (latest_market_structure == 'downtrend' or last_poi_support is None):
            self.algorithm.Transactions.CancelOrder(self.pending_order['order_id'], f"Order Tag #{self.pending_order['order_tag_id']}: Pending Order Cancelled (Market Structure Flipped or got None POI)")
            self.pending_order = None

        elif (self.pending_order is not None and self.pending_order['type'] == 'short') and (latest_market_structure == 'uptrend' or last_poi_resistance is None):
            self.algorithm.Transactions.CancelOrder(self.pending_order['order_id'], f"Order Tag #{self.pending_order['order_tag_id']}: Pending Order Cancelled (Market Structure Flipped or got None POI)")
            self.pending_order = None


        current_time = data.Time.time()
        start_time = time(1, 30)
        end_time = time(16, 00)

        day_of_week, day_count = self.GetDayOccurrenceInMonth()

        if True:
            self.PlaceTradeIfCriteriaMet()
        else:
            if self.pending_order is not None:
                self.algorithm.Transactions.CancelOrder(self.pending_order['order_id'], f"Order Tag #{self.pending_order['order_tag_id']}: Pending Order Cancelled (Out of Interval)")
                self.pending_order = None

        if current_time > end_time and day_of_week == 4:
            self.algorithm.liquidate()
            self.open_trades = []
            self.closed_trades = []

    def PlaceTradeIfCriteriaMet(self):
        self.account_risk_pct = self.params["ACCOUNT_RISK_PCT"]
        if not self.enable_multiple_positions and self.open_trades:
            return
        latest_market_structure = self.market_structure_algo_low.GetLatestMarketStructure()
        last_poi_support, last_poi_resistance = self.poi_algo.GetNearestPOIs()
        current_price = self.algorithm.Securities[self.symbol].Price
        
        # Calculate proximity to current price for support and resistance POIs
        support_proximity = float('inf') if last_poi_support is None else abs(current_price - last_poi_support['price'])
        resistance_proximity = float('inf') if last_poi_resistance is None else abs(current_price - last_poi_resistance['price'])
        
        if last_poi_support is not None and last_poi_support['pivot'] and current_price > last_poi_support['price'] and support_proximity <= resistance_proximity:
            self.SetAccountPCT('long')
            self.PlaceLongTrade(last_poi_support, last_poi_resistance)
        elif last_poi_resistance is not None and last_poi_resistance['pivot'] and current_price < last_poi_resistance['price'] and resistance_proximity <= support_proximity:
            self.SetAccountPCT('short')
            self.PlaceShortTrade(last_poi_support, last_poi_resistance)

    def SetAccountPCT(self, trade_type):
        latest_market_structure_low = self.market_structure_algo_low.GetLatestMarketStructure()
        latest_market_structure_high = self.market_structure_algo_high.GetLatestMarketStructure()
        if (trade_type == 'long' and latest_market_structure_high == 'downtrend') or (trade_type == 'short' and latest_market_structure_high == 'uptrend'):
            self.account_risk_pct /= 2

    def IsEntryPriceWithinImbalance(self, current_price, entry_price):
        nearest_above, nearest_below = self.imbalances.find_nearest_imbalances(current_price)
        if nearest_above is not None:
            above_prices = sorted(nearest_above[1:3])
            if above_prices[0] <= entry_price <= above_prices[1]:
                return True

        if nearest_below is not None:
            below_prices = sorted(nearest_below[1:3])
            if below_prices[0] <= entry_price <= below_prices[1]:
                return True

        return False

    def PlaceLongTrade(self, poi_support, poi_resistance):
        if not self.IsInImbalance(poi_support['price']):
            return
        #stop_loss_price = max(round(poi_support['pivot'] - (self.pip_value * 1.5), 5), round(poi_support['price'] - (self.pip_value * 10), 5))
        stop_loss_price = round(poi_support['pivot'] - (self.pip_value * 1.5), 5)
        if abs(poi_support['price'] - stop_loss_price) > (self.pip_value * 7) or abs(poi_support['price'] - stop_loss_price) < (self.pip_value * 0):
            return
        take_profit_price1 = round(poi_support['price'] + self.risk_reward_target_1 * (poi_support['price'] - stop_loss_price), 5)
        take_profit_price2 = round(poi_support['price'] + self.risk_reward_target_2 * (poi_support['price'] - stop_loss_price), 5)

        if self.pending_order is not None:
            if self.pending_order['type'] == 'long' and round(self.pending_order['entry_price'], 5) == round(poi_support['price'], 5) and \
                    self.pending_order['size'] == self.CalculateEntrySize(stop_loss_price, poi_support['price']):
                return

            self.algorithm.Transactions.CancelOrder(self.pending_order['order_id'], f"Order Tag #{self.pending_order['order_tag_id']}: Pending Order Canceled (New Long)")
            self.pending_order = None

        if not self.EntryBufferChecker(poi_support['price']):
            return

        risk_reward = self.CheckRiskRewardRatio('long', poi_support, poi_resistance)
        if risk_reward["isTrade"]:
            entry_size = self.CalculateEntrySize(stop_loss_price, poi_support['price'])
            if entry_size is None:
                self.algorithm.Debug(f"Insufficient margin for long trade. Required margin: {required_margin}, available margin: {self.algorithm.Portfolio.MarginRemaining}")
                return
            limit_order_price = round(poi_support['price'], 5)
            limit_order_ticket = self.algorithm.LimitOrder(self.symbol, entry_size, limit_order_price, f"Order Tag #{self.order_tag_id}: New Long Entry")

            self.pending_order = {
                'type': 'long',
                'entry_price': poi_support['price'],
                'stop_loss': stop_loss_price,
                'take_profit1': take_profit_price1,
                'take_profit2': None if risk_reward["tps"] == "1" else take_profit_price2,
                'size': entry_size,
                'initial_stop_loss': stop_loss_price,
                'order_id': limit_order_ticket.OrderId,
                'order_tag_id': self.order_tag_id
            }
            self.order_tag_id += 1

    def PlaceShortTrade(self, poi_support, poi_resistance):
        if not self.IsInImbalance(poi_resistance['price']):
            return
        #stop_loss_price = min(round(poi_resistance['pivot'] + (self.pip_value * 1.5), 5), round(poi_resistance['price'] + (self.pip_value * 10), 5))
        stop_loss_price = round(poi_resistance['pivot'] + (self.pip_value * 1.5), 5)
        if abs(poi_resistance['price'] - stop_loss_price) > (self.pip_value * 7) or abs(poi_resistance['price'] - stop_loss_price) < (self.pip_value * 0):
            return
        take_profit_price1 = round(poi_resistance['price'] - self.risk_reward_target_1 * (stop_loss_price - poi_resistance['price']), 5)
        take_profit_price2 = round(poi_resistance['price'] - self.risk_reward_target_2 * (stop_loss_price - poi_resistance['price']), 5)

        if self.pending_order is not None:
            if self.pending_order['type'] == 'short' and round(self.pending_order['entry_price'], 5) == round(poi_resistance['price'], 5) and \
                    self.pending_order['size'] == self.CalculateEntrySize(stop_loss_price, poi_resistance['price']):
                return

            self.algorithm.Transactions.CancelOrder(self.pending_order['order_id'], f"Order Tag #{self.pending_order['order_tag_id']}: Pending Order Cancelled (New Short)")
            self.pending_order = None

        if not self.EntryBufferChecker(poi_resistance['price']):
            return

        risk_reward = self.CheckRiskRewardRatio('short', poi_support, poi_resistance)
        if risk_reward["isTrade"]:
            entry_size = self.CalculateEntrySize(stop_loss_price, poi_resistance['price'])
            if entry_size is None:
                self.algorithm.Debug(f"Insufficient margin for short trade. Required margin: {required_margin}, available margin: {self.algorithm.Portfolio.MarginRemaining}")
                return
            limit_order_price = round(poi_resistance['price'], 5)
            limit_order_ticket = self.algorithm.LimitOrder(self.symbol, -entry_size, limit_order_price, f"Order Tag #{self.order_tag_id}: New Short Entry")

            self.pending_order = {
                'type': 'short',
                'entry_price': poi_resistance['price'],
                'stop_loss': stop_loss_price,
                'take_profit1': take_profit_price1,
                'take_profit2': None if risk_reward["tps"] == "1" else take_profit_price2,
                'size': entry_size,
                'initial_stop_loss': stop_loss_price,
                'order_id': limit_order_ticket.OrderId,
                'order_tag_id': self.order_tag_id
            }
            self.order_tag_id += 1

    def EntryBufferChecker(self, entry_price):
        buffer_distance = self.entry_buffer_pips * self.pip_value
        for trade in self.open_trades:
            if abs(trade['entry_price'] - entry_price) <= buffer_distance:
                return False
        return True

    def IsInImbalance(self, price):
        if not self.enable_imbalances:
            return True
        nearest_above, nearest_below = self.imbalances.find_nearest_imbalances(price)
        if nearest_above is not None:
            above_prices = sorted(nearest_above[1:3])
            if above_prices[0] <= price <= above_prices[1]:
                return True
        if nearest_below is not None:
            below_prices = sorted(nearest_below[1:3])
            if below_prices[0] <= price <= below_prices[1]:
                return True
        return False

    def UpdateStopLoss(self):
        if not self.enable_stoploss_update or not self.open_trades:
            return

        current_price = self.algorithm.Securities[self.symbol].Price

        for trade in self.open_trades:
            if trade['type'] == 'long' and current_price >= trade['entry_price'] + (trade['entry_price'] - trade['initial_stop_loss']) and trade['stop_loss'] != trade['entry_price'] + (self.stoploss_update_pips * self.pip_value):
                trade['stop_loss'] = trade['entry_price'] + (self.stoploss_update_pips * self.pip_value)
                self.algorithm.Transactions.CancelOrder(trade['stop_loss_order_id'], f"Order Tag #{trade['order_tag_id']}: SL")
                sl_order_ticket = self.algorithm.StopMarketOrder(self.symbol, -trade['size'], round(trade['stop_loss'], 5), f"Order Tag #{trade['order_tag_id']}: SL Updated")
                trade['stop_loss_order_id'] = sl_order_ticket.OrderId
            elif trade['type'] == 'short' and current_price <= trade['entry_price'] - (trade['initial_stop_loss'] - trade['entry_price']) and trade['stop_loss'] != trade['entry_price'] - (self.stoploss_update_pips * self.pip_value):
                trade['stop_loss'] = trade['entry_price'] - (self.stoploss_update_pips * self.pip_value)
                self.algorithm.Transactions.CancelOrder(trade['stop_loss_order_id'], f"Order Tag #{trade['order_tag_id']}: SL")
                sl_order_ticket = self.algorithm.StopMarketOrder(self.symbol, trade['size'], round(trade['stop_loss'], 5), f"Order Tag #{trade['order_tag_id']}: SL Updated")
                trade['stop_loss_order_id'] = sl_order_ticket.OrderId

    def OnOrderEvent(self, orderEvent):
        order = self.algorithm.Transactions.GetOrderById(orderEvent.OrderId)
        if orderEvent.Status != OrderStatus.Filled:
            return

        fee = self.algorithm.Securities[order.Symbol].FeeModel.GetOrderFee(OrderFeeParameters(self.algorithm.Securities[order.Symbol], order))

        def create_tp_order(size, price, tag):
            return self.algorithm.LimitOrder(self.symbol, size, round(price, 5), tag)

        def create_sl_order(size, price, order_type, tag):
            return self.algorithm.StopMarketOrder(self.symbol, size, round(price, 5), tag)

        if self.pending_order and orderEvent.OrderId == self.pending_order['order_id']:
            new_trade = self.pending_order.copy()
            self.open_trades.append(new_trade)
            self.pending_order = None

            sl_order_ticket = create_sl_order(-new_trade['size'] if new_trade['type'] == 'long' else new_trade['size'], new_trade['stop_loss'], new_trade['type'], f"Order Tag #{new_trade['order_tag_id']}: SL")
            if new_trade["take_profit2"] is None:
                tp1_order_ticket = create_tp_order(-new_trade['size'] if new_trade['type'] == 'long' else new_trade['size'], new_trade['take_profit1'], "TP1")
                new_trade.update({
                    'take_profit1_order_id': tp1_order_ticket.OrderId,
                    'take_profit2_order_id': None,
                    'stop_loss_order_id': sl_order_ticket.OrderId
                })
            else:
                tp1_size = round(new_trade['size'] * 0.66)
                tp2_size = new_trade['size'] - tp1_size
                tp1_order_ticket = create_tp_order(-tp1_size if new_trade['type'] == 'long' else tp1_size, new_trade['take_profit1'], f"Order Tag #{new_trade['order_tag_id']}: TP1")
                tp2_order_ticket = create_tp_order(-tp2_size if new_trade['type'] == 'long' else tp2_size, new_trade['take_profit2'], f"Order Tag #{new_trade['order_tag_id']}: TP2")
                new_trade.update({
                    'take_profit1_order_id': tp1_order_ticket.OrderId,
                    'take_profit2_order_id': tp2_order_ticket.OrderId,
                    'stop_loss_order_id': sl_order_ticket.OrderId
                })
            return

        for trade in self.open_trades:
            if orderEvent.OrderId == trade['stop_loss_order_id']:
                self.algorithm.Transactions.CancelOrder(trade['take_profit1_order_id'], f"Order Tag #{trade['order_tag_id']}: TP1")
                if 'take_profit2_order_id' in trade and trade['take_profit2_order_id'] is not None:
                    self.algorithm.Transactions.CancelOrder(trade['take_profit2_order_id'], f"Order Tag #{trade['order_tag_id']}: TP2")
                self.closed_trades.append(trade)
                self.open_trades.remove(trade)
                return

            elif orderEvent.OrderId == trade['take_profit1_order_id']:
                if trade['take_profit2_order_id'] is None:
                    self.algorithm.Transactions.CancelOrder(trade['stop_loss_order_id'], f"Order Tag #{trade['order_tag_id']}: SL")
                    self.closed_trades.append(trade)
                    self.open_trades.remove(trade)
                    return
                remaining_size = trade['size'] - abs(orderEvent.FillQuantity)
                self.algorithm.Transactions.CancelOrder(trade['stop_loss_order_id'], f"Order Tag #{trade['order_tag_id']}: SL")
                sl_order_ticket = create_sl_order(-remaining_size if trade['type'] == 'long' else remaining_size, trade['stop_loss'], trade['type'], f"Order Tag #{trade['order_tag_id']}: SL")
                trade['stop_loss_order_id'] = sl_order_ticket.OrderId
                return

            elif orderEvent.OrderId == trade['take_profit2_order_id']:
                self.algorithm.Transactions.CancelOrder(trade['take_profit1_order_id'], f"Order Tag #{trade['order_tag_id']}: TP1")
                self.algorithm.Transactions.CancelOrder(trade['stop_loss_order_id'], f"Order Tag #{trade['order_tag_id']}: SL")
                self.closed_trades.append(trade)
                self.open_trades.remove(trade)
                return


    def CalculateEntrySize(self, stop_loss_price, entry_price):
        leverage = self.algorithm.Securities[self.symbol].Leverage
        risk_per_trade = self.algorithm.Portfolio.Cash * self.account_risk_pct
        risk_amount = abs(entry_price - stop_loss_price)
        entry_size = int(risk_per_trade / risk_amount)
        entry_size_max = int(0.5 * 30 * self.algorithm.Portfolio.Cash / entry_price)
        entry_size = min(entry_size, entry_size_max)
        if entry_size < 500:
            entry_size = 0
        return entry_size

    def CheckRiskRewardRatio(self, trade_type, poi_support, poi_resistance):
        if trade_type == 'long':
            if poi_resistance is None:
                return {"isTrade": True, "tps": "1,2"}
            take_profit_price = poi_resistance['pivot']
            stop_loss_price = poi_support['pivot']
            entry_price = poi_support['price']
        elif trade_type == 'short':
            if poi_support is None:
                return {"isTrade": True, "tps": "1,2"}
            take_profit_price = poi_support['pivot']
            stop_loss_price = poi_resistance['pivot']
            entry_price = poi_resistance['price']

        risk_reward_ratio = abs(take_profit_price - entry_price) / abs(stop_loss_price - entry_price)
        return {"isTrade": True, "tps": "1,2"}

        if risk_reward_ratio < self.risk_reward_target_1:
            return {"isTrade": False, "tps": ""}
        elif self.risk_reward_target_1 <= risk_reward_ratio <= self.risk_reward_target_2:
            return {"isTrade": True, "tps": "1"}
        else:
            return {"isTrade": True, "tps": "1,2"}

    def FailSafeCleanUp(self):
        # First check for price-based fail-safes
        current_price = self.algorithm.Securities[self.symbol].Price
        
        for trade in self.open_trades[:]:
            if (trade['type'] == 'long' and current_price < trade['stop_loss']) or \
               (trade['type'] == 'short' and current_price > trade['stop_loss']):
                # Cancel all pending orders for this trade
                if trade['take_profit1_order_id'] is not None:
                    self.algorithm.Transactions.CancelOrder(trade['take_profit1_order_id'], 
                        f"Order Tag #{trade['order_tag_id']}: Emergency Cancel TP1")
                if trade['take_profit2_order_id'] is not None:
                    self.algorithm.Transactions.CancelOrder(trade['take_profit2_order_id'], 
                        f"Order Tag #{trade['order_tag_id']}: Emergency Cancel TP2")
                if trade['stop_loss_order_id'] is not None:
                    self.algorithm.Transactions.CancelOrder(trade['stop_loss_order_id'], 
                        f"Order Tag #{trade['order_tag_id']}: Emergency Cancel SL")
                
                # Liquidate position
                self.algorithm.liquidate()
                
                # Log the emergency action
                self.algorithm.Debug(f"Emergency failsafe triggered for {trade['type']} position. " + 
                                   f"Current price: {current_price}, Stop loss: {trade['stop_loss']}")
                
                # Reset trade lists
                self.open_trades = []
                self.closed_trades = []
                return

        # Original failsafe cleanup logic for closed trades
        toBeCancelledOrders = []

        for trade in self.closed_trades[:]:
            if 'take_profit1_order_id' in trade and trade['take_profit1_order_id'] is not None:
                tp1_order = self.algorithm.Transactions.GetOrderById(trade['take_profit1_order_id'])
                if tp1_order is not None:
                    toBeCancelledOrders.append((tp1_order, "TP1"))

            if 'take_profit2_order_id' in trade and trade['take_profit2_order_id'] is not None:
                tp2_order = self.algorithm.Transactions.GetOrderById(trade['take_profit2_order_id'])
                if tp2_order is not None:
                    toBeCancelledOrders.append((tp2_order, "TP2"))

            if 'stop_loss_order_id' in trade and trade['stop_loss_order_id'] is not None:
                sl_order = self.algorithm.Transactions.GetOrderById(trade['stop_loss_order_id'])
                if sl_order is not None:
                    toBeCancelledOrders.append((sl_order, "SL"))

            for order, order_label in toBeCancelledOrders:
                if order.Status == OrderStatus.Submitted:
                    self.algorithm.Transactions.CancelOrder(order.Id, 
                        f"Order Tag Id #{trade['order_tag_id']}: Cancelled Submitted Order from Closed Trades")
                    self.algorithm.Debug(f"{order_label} order canceling issue handled, executed fail-safe clean up and canceled it: Order Tag ID #{trade['order_tag_id']}")

            self.closed_trades.remove(trade)

    def OnEndOfAlgorithm(self):
        pass
