import pandas as pd
from datetime import datetime
from AlgorithmImports import *

class TradeTracker:
    def __init__(self):
        self.active_trade = None
        self.completed_trades = []
        
    def add_entry(self, entry_price, entry_size, entry_time):
        """Add a new trade entry to the tracker"""
        if self.active_trade is not None:
            print(f"WARNING: Attempting to add new trade while another trade is active. Completing current trade first.")
            # Force complete the current trade if not already completed
            if not self.is_trade_completed():
                # Mark the current trade as completed with the information we have
                self.get_trade_summary()
            
        self.active_trade = {
            'entry_price': entry_price,
            'entry_size': entry_size,
            'entry_time': entry_time,
            'tp1_price': None,
            'tp1_size': None,
            'tp1_time': None,
            'tp1_filled': False,
            'tp2_price': None,
            'tp2_size': None,
            'tp2_time': None,
            'tp2_filled': False,
            'sl_price': None,
            'sl_size': None,
            'sl_time': None,
            'sl_filled': False,
            'liquidation_price': None,
            'liquidation_size': None,
            'liquidation_time': None,
            'liquidation_filled': False
        }
        
    def update_tp1(self, price, size, fill_time):
        """Update TP1 details for the active trade"""
        if self.active_trade is None:
            # Create a dummy trade entry if no active trade exists
            self.add_entry(price, size, fill_time)
            
        self.active_trade['tp1_price'] = price
        self.active_trade['tp1_size'] = size
        self.active_trade['tp1_time'] = fill_time
        self.active_trade['tp1_filled'] = True
        
    def update_tp2(self, price, size, fill_time):
        """Update TP2 details for the active trade"""
        if self.active_trade is None:
            # Create a dummy trade entry if no active trade exists
            self.add_entry(price, size, fill_time)
            
        self.active_trade['tp2_price'] = price
        self.active_trade['tp2_size'] = size
        self.active_trade['tp2_time'] = fill_time
        self.active_trade['tp2_filled'] = True
        
    def update_sl(self, price, size, fill_time):
        """Update stop loss details for the active trade"""
        if self.active_trade is None:
            # Create a dummy trade entry if no active trade exists
            self.add_entry(price, size, fill_time)
            
        self.active_trade['sl_price'] = price
        self.active_trade['sl_size'] = size
        self.active_trade['sl_time'] = fill_time
        self.active_trade['sl_filled'] = True
        
    def update_liquidation(self, price, size, fill_time):
        """Update liquidation details for the active trade"""
        if self.active_trade is None:
            # Create a dummy trade entry if no active trade exists
            self.add_entry(price, size, fill_time)
            
        self.active_trade['liquidation_price'] = price
        self.active_trade['liquidation_size'] = size
        self.active_trade['liquidation_time'] = fill_time
        self.active_trade['liquidation_filled'] = True
        
    def is_trade_completed(self):
        """Check if the active trade is completed (either TP2, SL, or liquidation filled)"""
        if self.active_trade is None:
            return False
            
        completed = (self.active_trade['tp2_filled'] or 
                    self.active_trade['sl_filled'] or 
                    self.active_trade['liquidation_filled'])
                    
        if completed:
            print(f"Trade completed - TP2: {self.active_trade['tp2_filled']}, "
                  f"SL: {self.active_trade['sl_filled']}, "
                  f"Liquidation: {self.active_trade['liquidation_filled']}")
        else:
            print(f"Trade not completed - TP2: {self.active_trade['tp2_filled']}, "
                  f"SL: {self.active_trade['sl_filled']}, "
                  f"Liquidation: {self.active_trade['liquidation_filled']}")
            
        return completed
        
    def get_trade_summary(self):
        """Get a summary of the completed trade"""
        if not self.is_trade_completed():
            return None
            
        summary = {
            'entry_time': self.active_trade['entry_time'],
            'entry_price': self.active_trade['entry_price'],
            'entry_size': self.active_trade['entry_size'],
            'exit_time': None,
            'exit_price': None,
            'exit_size': None,
            'exit_type': None,
            'profit_loss': None
        }
        
        if self.active_trade['tp1_filled']:
            summary['exit_time'] = self.active_trade['tp1_time']
            summary['exit_price'] = self.active_trade['tp1_price']
            summary['exit_size'] = self.active_trade['tp1_size']
            summary['exit_type'] = 'TP1'
        elif self.active_trade['tp2_filled']:
            summary['exit_time'] = self.active_trade['tp2_time']
            summary['exit_price'] = self.active_trade['tp2_price']
            summary['exit_size'] = self.active_trade['tp2_size']
            summary['exit_type'] = 'TP2'
        elif self.active_trade['sl_filled']:
            summary['exit_time'] = self.active_trade['sl_time']
            summary['exit_price'] = self.active_trade['sl_price']
            summary['exit_size'] = self.active_trade['sl_size']
            summary['exit_type'] = 'SL'
        elif self.active_trade['liquidation_filled']:
            summary['exit_time'] = self.active_trade['liquidation_time']
            summary['exit_price'] = self.active_trade['liquidation_price']
            summary['exit_size'] = self.active_trade['liquidation_size']
            summary['exit_type'] = 'LIQUIDATION'
            
        # Calculate profit/loss
        if summary['exit_type'] in ['TP1', 'TP2']:
            summary['profit_loss'] = (summary['exit_price'] - summary['entry_price']) * summary['entry_size']
        else:  # SL or LIQUIDATION
            summary['profit_loss'] = (summary['entry_price'] - summary['exit_price']) * summary['entry_size']
            
        # Move completed trade to history and clear active trade
        self.completed_trades.append(self.active_trade)
        self.active_trade = None
            
        return summary
        
    def get_completed_trades(self):
        """Return list of all completed trades"""
        return self.completed_trades 