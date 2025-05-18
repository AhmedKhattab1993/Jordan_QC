from AlgorithmImports import *
class ParamsReader:
    def __init__(self, algorithm):
        self.algorithm = algorithm

    def get_params(self):
        #if year == 1:
        #    start_date = "2021-09-01"
        #    end_date = "2022-09-01"
        #elif year == 2:
        #    start_date = "2022-09-01"
        #    end_date = "2023-09-01"
        #elif year == 3:
        #    start_date = "2023-09-01"
        #    end_date = "2024-09-01"

        start_date = "2024-1-1"
        end_date = "2025-05-1"
        params = {
            # General Params
            "symbol": self.algorithm.GetParameter("symbol", "EURUSD"),
            "startDate": {
                "year": int(self.algorithm.GetParameter("startDate", start_date).split('-')[0]),
                "month": int(self.algorithm.GetParameter("startDate", start_date).split('-')[1]),
                "day": int(self.algorithm.GetParameter("startDate", start_date).split('-')[2])
            },
            "endDate": {
                "year": int(self.algorithm.GetParameter("endDate", end_date).split('-')[0]),
                "month": int(self.algorithm.GetParameter("endDate", end_date).split('-')[1]),
                "day": int(self.algorithm.GetParameter("endDate", end_date).split('-')[2])
            },
            "LOW_TF": int(self.algorithm.GetParameter("LOW_TF", 5)),
            "HIGH_TF": int(self.algorithm.GetParameter("HIGH_TF", 15)),

            # Set with 0 to disable
            "FIXED_FEE": float(self.algorithm.GetParameter("FIXED_FEE", 0)),
            "PCT_FEE": float(self.algorithm.GetParameter("PCT_FEE", 0)) / 100,


            # POI Params
            "POINT_OF_INTEREST_G1_MIN": int(self.algorithm.GetParameter("POINT_OF_INTEREST_G1_MIN", 1)),
            "POINT_OF_INTEREST_G1_MAX": int(self.algorithm.GetParameter("POINT_OF_INTEREST_G1_MAX", 1)),
            "POINT_OF_INTEREST_G2_MIN": int(self.algorithm.GetParameter("POINT_OF_INTEREST_G2_MIN", 1)),
            "POINT_OF_INTEREST_G2_MAX": int(self.algorithm.GetParameter("POINT_OF_INTEREST_G2_MAX", 2)),
            "POINT_OF_INTEREST_MULTIPLE": float(self.algorithm.GetParameter("POINT_OF_INTEREST_MULTIPLE", 3)),
            "POINT_OF_INTEREST_PIVOTS_BARS": int(self.algorithm.GetParameter("POINT_OF_INTEREST_PIVOTS_BARS", 3)),

            # Market Structure Params
            "MARKET_STRUCTURE_BARS": int(self.algorithm.GetParameter("MARKET_STRUCTURE_BARS", 7)),

            # Strategy 1 Params
            "RISK_REWARD_TARGET_1": float(self.algorithm.GetParameter("RISK_REWARD_TARGET_1", 3)),
            "RISK_REWARD_TARGET_2": float(self.algorithm.GetParameter("RISK_REWARD_TARGET_2", 7)),
            "ENABLE_IMBALANCES": self.algorithm.GetParameter("ENABLE_IMBALANCES", "false").lower() == "true",
            "ACCOUNT_RISK_PCT": float(self.algorithm.GetParameter("ACCOUNT_RISK_PCT", 1.0)) / 100,
            "ENABLE_STOPLOSS_UPDATE": self.algorithm.GetParameter("ENABLE_STOPLOSS_UPDATE", "false").lower() == "true",
            "STOPLOSS_UPDATE_PIPS": float(self.algorithm.GetParameter("STOPLOSS_UPDATE_PIPS", 0)),
            "ENABLE_MULTIPLE_POSITIONS": self.algorithm.GetParameter("ENABLE_MULTIPLE_POSITIONS", "false").lower() == "true",
            "ENTRY_BUFFER_PIPS": float(self.algorithm.GetParameter("ENTRY_BUFFER_PIPS", 1.5)),

            # Imbalances Params
            "IMBALANCES_TF": int(self.algorithm.GetParameter("IMBALANCES_TF", 3)),
            "GAPS_IMBALANCES_FACTOR": float(self.algorithm.GetParameter("GAPS_IMBALANCES_FACTOR", 1.5)),
            "GAPS_IMBALANCES_AVG_N": int(self.algorithm.GetParameter("GAPS_IMBALANCES_AVG_N", 10)),
            "BAR_BODY_IMBALANCES_FACTOR": float(self.algorithm.GetParameter("BAR_BODY_IMBALANCES_FACTOR", 1.5)),
            "BAR_BODY_IMBALANCES_N": int(self.algorithm.GetParameter("BAR_BODY_IMBALANCES_N", 10)),
            "MULTIPLE_BARS_IMBALANCES_N": int(self.algorithm.GetParameter("MULTIPLE_BARS_IMBALANCES_N", 8)),
            "BARS_WICKS_IMBALANCES_N": int(self.algorithm.GetParameter("BARS_WICKS_IMBALANCES_N", 10)),
            "BARS_WICKS_IMBALANCES_FACTOR": float(self.algorithm.GetParameter("BARS_WICKS_IMBALANCES_FACTOR", 1.5)),
            "IMBALANCES_FILL_PCT": float(self.algorithm.GetParameter("IMBALANCES_FILL_PCT", 10)) / 100,
            "ENABLE_GAPS": self.algorithm.GetParameter("ENABLE_GAPS", "true").lower() == "true",
            "ENABLE_BODY": self.algorithm.GetParameter("ENABLE_BODY", "true").lower() == "true",
            "ENABLE_MULTIPLE": self.algorithm.GetParameter("ENABLE_MULTIPLE", "true").lower() == "true",
            "ENABLE_WICK": self.algorithm.GetParameter("ENABLE_WICK", "true").lower() == "true",
        }
        return params
