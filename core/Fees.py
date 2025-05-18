from AlgorithmImports import *

class FixedFeeModel(FeeModel):
    def __init__(self, fee):
        self.fee = fee

    def GetOrderFee(self, parameters):
        return OrderFee(CashAmount(self.fee, parameters.Security.QuoteCurrency.Symbol))

class PercentageFeeModel(FeeModel):
    def __init__(self, percentage):
        self.percentage = percentage

    def GetOrderFee(self, parameters):
        order_value = parameters.Security.Price * parameters.Order.AbsoluteQuantity
        fee = order_value * self.percentage
        return OrderFee(CashAmount(fee, parameters.Security.QuoteCurrency.Symbol))
