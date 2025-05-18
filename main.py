from AlgorithmImports import *
from strategies.Strategy1 import Strategy1
from helpers.ParamsReader import ParamsReader
from core.Fees import FixedFeeModel, PercentageFeeModel
from trade_tracker import TradeTracker

class SimpleCustomFillModel(FillModel):
    def __init__(self):
        super().__init__()

    def _create_order_event(self, asset, order):
        utc_time = Extensions.convert_to_utc(asset.local_time, asset.exchange.time_zone)
        return OrderEvent(order, utc_time, OrderFee.ZERO)

    def _set_order_event_to_filled(self, fill, fill_price, fill_quantity):
        fill.status = OrderStatus.FILLED
        fill.fill_quantity = fill_quantity
        fill.fill_price = fill_price
        return fill

    def _get_trade_bar(self, asset, order_direction):
        trade_bar = asset.cache.get_data[TradeBar]()
        if trade_bar: return trade_bar

        # Tick-resolution data doesn't have TradeBar, use the asset price
        price = asset.price
        return TradeBar(asset.local_time, asset.symbol, price, price, price, price, 0)

    def market_fill(self, asset, order):
        fill = self._create_order_event(asset, order)
        if order.status == OrderStatus.CANCELED: return fill

        return self._set_order_event_to_filled(fill,
            asset.cache.ask_price \
                if order.direction == OrderDirection.BUY else asset.cache.bid_price,
            order.quantity)

    def stop_market_fill(self, asset, order):
        fill = self._create_order_event(asset, order)
        if order.status == OrderStatus.CANCELED: return fill

        stop_price = order.stop_price
        trade_bar = self._get_trade_bar(asset, order.direction)

        if order.direction == OrderDirection.SELL and trade_bar.low < stop_price:
            return self._set_order_event_to_filled(fill, stop_price, order.quantity)

        if order.direction == OrderDirection.BUY and trade_bar.high > stop_price:
            return self._set_order_event_to_filled(fill, stop_price, order.quantity)

        return fill

    def limit_fill(self, asset, order):
        fill = self._create_order_event(asset, order)
        if order.status == OrderStatus.CANCELED: return fill

        limit_price = order.limit_price
        trade_bar = self._get_trade_bar(asset, order.direction)

        if order.direction == OrderDirection.SELL and trade_bar.high > limit_price:
            return self._set_order_event_to_filled(fill, limit_price, order.quantity)

        if order.direction == OrderDirection.BUY and trade_bar.low < limit_price:
            return self._set_order_event_to_filled(fill, limit_price, order.quantity)

        return fill

class Main(QCAlgorithm):
    def Initialize(self):
        params = ParamsReader(self).get_params()
        self.fixed_fee = params["FIXED_FEE"]
        self.pct_fee = params["PCT_FEE"]
        self.SetStartDate(params["startDate"]["year"], params["startDate"]["month"], params["startDate"]["day"])
        self.SetEndDate(params["endDate"]["year"], params["endDate"]["month"], params["endDate"]["day"])
        self.SetCash(10000)
        self.forex = self.AddForex(params["symbol"], Resolution.SECOND)
        #self.forex.SetBrokerageModel(BrokerageName.OandaBrokerage, AccountType.Margin)
        self.forex.SetLeverage(30)
        self.forex.set_fill_model(SimpleCustomFillModel())

        if self.fixed_fee != 0 and self.pct_fee == 0:
            self.forex.SetFeeModel(FixedFeeModel(self.fixed_fee))
        elif self.pct_fee != 0 and self.fixed_fee == 0:
            self.forex.SetFeeModel(PercentageFeeModel(self.pct_fee))

        self.set_time_zone(TimeZones.NEW_YORK)
        self.strategy = Strategy1(params)
        self.strategy.Initialize(self)
        
        # Initialize the trade tracker
        self.trade_tracker = TradeTracker()
        # Dictionary to keep track of active trades
        self.active_trades = {}

    def OnData(self, data):
        self.strategy.UpdateStopLoss()
        self.strategy.FailSafeCleanUp()

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.FILLED:
            order = self.Transactions.GetOrderById(orderEvent.OrderId)
            #self.Log(f"Order Filled - Time: {self.Time}, Tag: {order.Tag}, Price: {orderEvent.FillPrice}, Quantity: {orderEvent.FillQuantity}")
            
            # Track the order based on its tag
            if "New Short Entry" in order.Tag or "New Long Entry" in order.Tag:
                self.trade_tracker.add_entry(
                    entry_price=orderEvent.FillPrice,
                    entry_size=orderEvent.FillQuantity,
                    entry_time=self.Time
                )
            
            elif "TP1" in order.Tag:
                self.trade_tracker.update_tp1(
                    price=orderEvent.FillPrice,
                    size=orderEvent.FillQuantity,
                    fill_time=self.Time
                )
            
            elif "TP2" in order.Tag:
                self.trade_tracker.update_tp2(
                    price=orderEvent.FillPrice,
                    size=orderEvent.FillQuantity,
                    fill_time=self.Time
                )
                # Check if trade is completed and log it
                if self.trade_tracker.is_trade_completed():
                    summary = self.trade_tracker.get_trade_summary()

            
            elif "SL" in order.Tag:
                self.trade_tracker.update_sl(
                    price=orderEvent.FillPrice,
                    size=orderEvent.FillQuantity,
                    fill_time=self.Time
                )
                # Check if trade is completed and log it
                if self.trade_tracker.is_trade_completed():
                    summary = self.trade_tracker.get_trade_summary()

            
            elif "Liquidated" in order.Tag:
                self.trade_tracker.update_liquidation(
                    price=orderEvent.FillPrice,
                    size=orderEvent.FillQuantity,
                    fill_time=self.Time
                )
                # Check if trade is completed and log it
                if self.trade_tracker.is_trade_completed():
                    summary = self.trade_tracker.get_trade_summary()
                    
        self.strategy.OnOrderEvent(orderEvent)

    def OnEndOfAlgorithm(self):
        # Log CSV header with all available fields
        self.Log(",Entry Time,Entry Price,Entry Size,TP1 Price,TP1 Size,TP1 Time,TP1 Filled,"
                "TP2 Price,TP2 Size,TP2 Time,TP2 Filled,SL Price,SL Size,SL Time,SL Filled,"
                "Liquidation Price,Liquidation Size,Liquidation Time,Liquidation Filled,"
                "Exit Time,Exit Price,Exit Type,Profit/Loss")
        
        # Log all completed trades in CSV format
        for trade in self.trade_tracker.get_completed_trades():
            # Determine exit details
            exit_time = None
            exit_price = None
            exit_type = None
            
            if trade['tp1_filled']:
                exit_time = trade['tp1_time']
                exit_price = trade['tp1_price']
                exit_type = 'TP1'
            elif trade['tp2_filled']:
                exit_time = trade['tp2_time']
                exit_price = trade['tp2_price']
                exit_type = 'TP2'
            elif trade['sl_filled']:
                exit_time = trade['sl_time']
                exit_price = trade['sl_price']
                exit_type = 'SL'
            elif trade['liquidation_filled']:
                exit_time = trade['liquidation_time']
                exit_price = trade['liquidation_price']
                exit_type = 'LIQUIDATION'
                
            # Calculate profit/loss
            profit_loss = None
            if exit_type in ['TP1', 'TP2']:
                profit_loss = (exit_price - trade['entry_price']) * trade['entry_size']
            elif exit_type in ['SL', 'LIQUIDATION']:
                profit_loss = (trade['entry_price'] - exit_price) * trade['entry_size']
                
            # Log in CSV format with all fields
            self.Log(f",{trade['entry_time']},{trade['entry_price']},{trade['entry_size']},"
                   f"{trade['tp1_price']},{trade['tp1_size']},{trade['tp1_time']},{trade['tp1_filled']},"
                   f"{trade['tp2_price']},{trade['tp2_size']},{trade['tp2_time']},{trade['tp2_filled']},"
                   f"{trade['sl_price']},{trade['sl_size']},{trade['sl_time']},{trade['sl_filled']},"
                   f"{trade['liquidation_price']},{trade['liquidation_size']},{trade['liquidation_time']},{trade['liquidation_filled']},"
                   f"{exit_time},{exit_price},{exit_type},{profit_loss}")
                   
        self.strategy.OnEndOfAlgorithm()