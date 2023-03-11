#!/usr/bin/env python
# -*- coding: utf-8 -*-

from quanttrader.strategy.strategy_base import StrategyBase
from quanttrader.data.tick_event import TickType
from quanttrader.order.order_event import OrderEvent
from quanttrader.order.order_type import OrderType
from datetime import datetime, time, timedelta
from pathlib import Path
import pandas as pd
import logging
import queue
from twilio.rest import Client
import chime
import talib
import matplotlib.pyplot as plt
import argparse
import csv
import os
import msvcrt
import tkinter as tk

# Twilio SMS Stuff
account_sid = 'AC87cdc55ff3b08f617de9272d6d7ba1f6'
auth_token = 'a01d0329f48ba7f994476e13d88d7ae2'
twilio_number = '+18556453140'
target_number = '+18062360606'
client = Client(account_sid, auth_token)

_logger = logging.getLogger('qtlive')

#global parser
def create_parser():
    global parser
    parser = argparse.ArgumentParser(description='Live Engine')
    return parser


class DualTimeFrameStrategy(StrategyBase):

    def __init__(self):

        super().__init__()

        ## Indicators
        self.df_SMA = 0.0
        self.df_EMA = 0.0
        self.df_STD = 0.0
        self.df_RSI = 0.0
        self.df_SMA_UpperBand = 0.0      # Upper Bollinger Band about df_SMA
        self.df_SMA_LowerBand = 0.0      # Lower Bollinger Band about df_SMA
        self.df_StdDev = 2.0
        self.df_SecsPerBar = 20
        self.df_NumOfBars = 20
        self.rsi_over_bought = 70
        self.rsi_over_sold = 30
        self.df_index = -1
        
        # Timers
        self.rth_start_time = '09:30:00'
        self.start_time = '09:31:00'     
        self.end_time = '15:59:00'
           
        # PnL
        self.rPnL = 0.0
        self.uPnL = 0.0
        self.tPnL = 0.0
        self.max_tPnL = -1000000.0
        self.min_tPnL = 1000000.0
        self.max_uPnL = -1000000.0

        # Files
        self.backTestFilePathAndName = ''

        # Shares
        self.longBuyPrice = 0.0
        self.shortSellPrice = 0.0
        self.startingPosition = 0.0
        self.endingPosition = 0.0
        self.currentPosition = 0.0
        self.commissionPerShare = 0.005
        self.orderSize = 1

        # Counters
        self.totalBuySellCount = -1
        self.tickNumber = 0

        # Open - Close prices
        self.priceOpen = 0.0
        self.priceClose = 0.0
        self.priceChange = 0.0

        # Price Slope Trade
        self.priceSlope = 0.0
        self.priceCtr = 0
        self.priceStart = 0.0
        self.priceSum = 0.0
        self.priceAvg = 0.0
        self.priceSlopeThreshold = 0.5
   
        # Price Slope Day
        self.priceSlopeDay = 0.0
        self.priceCtrDay = 0
        self.priceStartDay = 0.0
        self.priceSumDay = 0.0
        self.priceAvgDay = 0.0

        # Brokerage
        self.commissionTotal = 0.0

        # Max Loss
        self.maxLossDollars = 500

        # Buy - Sell Logic
        self.goLong = False
        self.goShort = False

        # max uPnL Profit
        self.Max_uPnL_Reached = False
        self.Max_uPnL_Threshold = 0.0
        self.Max_uPnL_PercentOfMax = 80.0
        self.Max_uPnL_DollarsPerShare = 10.0

        # Switches
        self.backTestSwt = True
        self.verboseSwt = True
        self.sendSmsMsgs = True
        self.settings = True

        # CSV Stuff
        self.csvWrite = False
        self.csvFileName = 'QuantTrader00.csv'

        # System logic
        self.endTrading = False
        self.strategyStopped = False
        self.msg_sent = True

        # Parms
        self.displayParms = []
        self.filename = ''

        # Global 'self'
        global btSelf
        btSelf = self

        _logger.info('DualTimeFrameStrategy initiated')



        
    #def change_variables(self):
    #    if self.settings:
    #        # Create a new popup window
    #        popup_window = tk.Toplevel()
    #        popup_window.title("Change Variables")
    #        popup_window.geometry("300x200")

    #        # Create input fields for each variable
    #        end_time_label = tk.Label(popup_window, text="End Time:")
    #        end_time_label.grid(row=0, column=0, padx=5, pady=5)
    #        end_time_entry = tk.Entry(popup_window)
    #        end_time_entry.grid(row=0, column=1, padx=5, pady=5)

    #        long_buy_price_label = tk.Label(popup_window, text="Long Buy Price:")
    #        long_buy_price_label.grid(row=1, column=0, padx=5, pady=5)
    #        long_buy_price_entry = tk.Entry(popup_window)
    #        long_buy_price_entry.grid(row=1, column=1, padx=5, pady=5)

    #        tick_number_label = tk.Label(popup_window, text="Tick Number:")
    #        tick_number_label.grid(row=2, column=0, padx=5, pady=5)
    #        tick_number_entry = tk.Entry(popup_window)
    #        tick_number_entry.grid(row=2, column=1, padx=5, pady=5)

    #        back_test_swt_label = tk.Label(popup_window, text="Back Test Switch:")
    #        back_test_swt_label.grid(row=3, column=0, padx=5, pady=5)
    #        back_test_swt_entry = tk.Entry(popup_window)
    #        back_test_swt_entry.grid(row=3, column=1, padx=5, pady=5)

    #        # Add a submit button that updates the variables and closes the window
    #        submit_button = tk.Button(popup_window, text="Submit", command=lambda: self.update_variables(end_time_entry.get(), float(long_buy_price_entry.get()), int(tick_number_entry.get()), bool(back_test_swt_entry.get())))
    #        submit_button.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

    #        # Make sure the window stays on top
    #        popup_window.attributes('-topmost', True)
    #    else:
    #        # If settings is False, do nothing
    #        pass

    #def update_variables(self, end_time, long_buy_price, tick_number, back_test_swt):
    #    # Update the variables
    #    self.end_time = end_time
    #    self.longBuyPrice = long_buy_price
    #    self.tickNumber = tick_number
    #    self.backTestSwt = back_test_swt

    #    # Set settings to False to close the popup window
    #    #self.settings = False


    def change_variables(self):
        if self.settings:
            # Create a new instance of the MyGUI class
            gui = MyGUI(self)

            # Set settings to False to close the popup window
            self.settings = False
        else:
            # If settings is False, do nothing
            pass

    def update_variables(self, end_time, long_buy_price, tick_number, back_test_swt):
        # Update the variables
        self.end_time = end_time
        self.longBuyPrice = long_buy_price
        self.tickNumber = tick_number
        self.backTestSwt = back_test_swt

        # Set settings to True to allow the popup window to be opened again
        self.settings = True


    def SqLiteWriteData(self):
        if self.csvWrite:

            self.tPnL = round(self.tPnL, 2)
            self.min_tPnL = round(self.min_tPnL, 2)
            self.max_tPnL = round(self.max_tPnL, 2)

            # Create header and row Combo
            headerRow = [
                'RunTime',datetime.today(),
                'Start',self.start_time,
                'End',self.end_time,
                'TickFile',self.filename,
                'Symbol',self.symbols,
                'Order Size',self.orderSize,
                'Start Size',self.startingPosition,
                'End Size',self.endingPosition,

                'BuySellCnt',self.totalBuySellCount,
                'tPnL',self.tPnL,
                'Min tPnL',self.min_tPnL,
                'Max tPnL',self.max_tPnL,

                'PriceSlopeDay',self.priceSlopeDay,
                'PriceSlopeTrade',self.priceSlope,
                'PriceSlopeThresh',self.priceSlopeThreshold,
                'PriceOpen',self.priceOpen,
                'PriceClose',self.priceClose,
                'PriceChange',self.priceChange,

                'Bar Size',self.df_SecsPerBar,
                'Num Bars',self.df_NumOfBars,
                'RSI Upper',self.rsi_over_bought,
                'RSI Lower',self.rsi_over_sold,
                'Max Loss',self.maxLossDollars,
                'Max uPnL',self.Max_uPnL_Reached,
                'uPnL Tresh',self.Max_uPnL_Threshold,
                '% Thresh',self.Max_uPnL_PercentOfMax,
                'Max $/Share',self.Max_uPnL_DollarsPerShare                
                ]

            # Extract the even-indexed elements (i.e., the column headers)
            header = headerRow[::2]

            # Extract the odd-indexed elements (i.e., the row values)
            row = headerRow[1::2]

            # Check if file exists
            if not os.path.exists(self.csvFileName):
                # If file does not exist, create it and write the header row
                with open(self.csvFileName, mode='w', newline='') as file:
                    msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)  # acquire lock
                    writer = csv.writer(file)
                    writer.writerow(header)
                    msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)  # release lock
                    # End of 'with' block - file will be automatically closed

            # Append new data row to the file
            with open(self.csvFileName, mode='a', newline='') as file:
                msvcrt.locking(file.fileno(), msvcrt.LK_LOCK, 1)  # acquire lock
                writer = csv.writer(file)
                writer.writerow(row)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)  # release lock
                # End of 'with' block - file will be automatically closed

            # Write Only Row Once and stop trading
            self.csvWrite = False
            self.strategyStopped = True

    def Self():
        return btSelf

    def SmsSend(self, message):
        try:
            client.messages.create(
            body=message,
            from_=twilio_number,
            to=target_number
            )
        except:
            print('Unable Twilio Authenticate - def SmsSend(self, message):')

    def PortfolioMsg(self, k, txtStr):
        self.tPnL = self.rPnL + self.uPnL
        self.max_uPnL = max(self.max_uPnL, self.uPnL)
        self.max_tPnL = max(self.max_tPnL, self.tPnL)
        self.min_tPnL = min(self.min_tPnL, self.tPnL)
        t = k.timestamp
        message = f'{t}, TICK {self.tickNumber}, \
POSITION {self.currentPosition}, \
Price {k.price}, \
PnL{self.totalBuySellCount}: rPnL {round(self.rPnL,2)} | uPnL {round(self.uPnL,2)} | tPnL {round(self.tPnL,2)} | min_tPnL {round(self.min_tPnL,2)} | max_tPnL {round(self.max_tPnL,2)} | '\
+ txtStr
        return message

    def SmsMsgUpdate(self, k):
        a = datetime.now().minute
        if (a % 5) == 0: 
            if not self.msg_sent:
                self.SmsSend(self.PortfolioMsg(k, "5 MIN UPDATE"))
                self.msg_sent = True
        else:
            self.msg_sent = False

    def LogTxt(self, t, k, txtStr, forceDisplay):
        if self.verboseSwt or forceDisplay:  _logger.info(self.PortfolioMsg(k, txtStr + f" Slopes |{round(self.priceSlopeDay,2)}|{round(self.priceSlope,2)}|"))


    def set_params(self, params_dict=None):
        global parser

        super().set_params(params_dict)

        args = parser.parse_args()
        config_file_path = args.config_file
        backtest_file_path = args.backtest_file

        # Append the new parameters to params_dict
        params_dict.update({
            'config_file_path': config_file_path,
            'backtest_file_path': backtest_file_path
        })

        if backtest_file_path != None:
            self.backTestSwt = True
            self.backTestFilePathAndName = backtest_file_path

        self.currentPosition = self.startingPosition
        
        # If backtesting change today to backtest date
        today = datetime.today()
        if self.backTestSwt:
            self.sendSmsMsgs = False
            p = Path(self.backTestFilePathAndName)
            self.filename = p.stem
            today = today.replace(year=int(self.filename[0:4]), month=int(self.filename[4:6]), day=int(self.filename[6:8]))
        self.rth_start_time = today.replace(hour=9, minute=25, second=0, microsecond=0)
        self.start_time = today.replace(hour=int(self.start_time[:2]), minute=int(self.start_time[3:5]), second=int(self.start_time[6:]), microsecond=0)
        self.end_time = today.replace(hour=int(self.end_time[:2]), minute=int(self.end_time[3:5]), second=int(self.end_time[6:]), microsecond=0)

        seconds = (self.end_time - self.start_time).seconds + 1  
        self.df_bar = pd.DataFrame(index=range(seconds), columns=['Open', 'High', 'Low', 'Close', 'Volume'])

    def ClosePosition(self, k):
        self.priceCtr = 0
        if self.currentPosition != self.endingPosition:
            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size = -self.currentPosition + self.endingPosition
            self.totalBuySellCount += 1
            commission = abs(self.commissionPerShare * o.order_size)
            self.commissionTotal -= commission
            self.rPnL -= commission
            self.rPnL += self.uPnL
            self.uPnL = 0.0
            self.tPnL = self.rPnL
            self.max_uPnL = max(self.max_uPnL, self.uPnL)
            self.max_tPnL = max(self.max_tPnL, self.tPnL)
            self.min_tPnL = min(self.min_tPnL, self.tPnL)
            self.currentPosition = self.endingPosition
            if not self.backTestSwt: self.place_order(o)
            if self.sendSmsMsgs: self.SmsSend(self.PortfolioMsg(k, "CLOSE POSITIONS"))
        self.endTrading = False


    def ParmsDisplay(self, k):

        self.tPnL = round(self.tPnL, 2)
        self.min_tPnL = round(self.min_tPnL, 2)
        self.max_tPnL = round(self.max_tPnL, 2)

        self.displayParms = ["self.start_time","self.end_time","self.backTestFilePathAndName","self.symbols",\
		"self.backTestSwt","self.sendSmsMsgs","self.verboseSwt",\
        "self.orderSize","self.startingPosition","self.endingPosition",\
        "self.df_SMA","self.df_EMA","self.df_STD","self.df_RSI","self.df_SMA_UpperBand","self.df_SMA_LowerBand",\
        "self.df_StdDev","self.df_SecsPerBar","self.df_NumOfBars","self.rsi_over_bought","self.rsi_over_sold",\
        "self.commissionPerShare","self.commissionTotal",\
        "self.maxLossDollars","self.Max_uPnL_Reached","self.Max_uPnL_Threshold","self.Max_uPnL_PercentOfMax","self.Max_uPnL_DollarsPerShare","self.totalBuySellCount",\
        "self.tPnL","self.min_tPnL","self.max_tPnL","self.priceSlope","self.priceSlopeDay","self.priceSlopeThreshold",\
        "self.priceOpen","self.priceClose","self.priceChange"]
            
        _logger.info('')
        _logger.info('*** DISPLAY PARMS START')
        for x in self.displayParms:
            _logger.info(f'{x} = {eval(x)}')
        _logger.info('')
        _logger.info(self.PortfolioMsg(k, 'PARMS END'))
        _logger.info('')

    def MaxLossCheck(self, t, k):       
        if self.currentPosition != 0 and self.uPnL <= -abs(self.maxLossDollars):
            self.endTrading = True
            self.LogTxt(t, k, '*** LOSS LIMIT REACHED = ' + str(round(int(self.uPnL),0)), True)
            return True
        return False

    def Max_uPnL_Check(self, t, k):
        if self.currentPosition != 0.0:
            if  self.uPnL >= self.Max_uPnL_Threshold and not self.Max_uPnL_Reached:
                self.LogTxt(t, k, '*** Max uPnL REACHED = ' + str(round(int(self.uPnL),0)), True)
                self.Max_uPnL_Reached = True
                return False
            elif self.Max_uPnL_Reached and self.uPnL <= self.max_uPnL * self.Max_uPnL_PercentOfMax / 100: 
                self.endTrading = True
                self.LogTxt(t, k, '*** Max uPnL EXECUTED = ' + str(round(int(self.uPnL),0)), True)
                self.Max_uPnL_Reached = False
                return True 
        return False

    def init_dual_time_frame_rule(self, k):
        price = k.price
        self.Max_uPnL_Threshold = abs(self.Max_uPnL_DollarsPerShare * self.orderSize)
        self.longBuyPrice = price
        self.shortSellPrice = price
        self.ParmsDisplay(k)
        if self.sendSmsMsgs: self.SmsSend(f'{k.timestamp}, INITIALIZE, PRICE = ${round(k.price, 2)}')


    def on_tick(self, k):

        super().on_tick(k)
        if not self.backTestSwt: 
            if k.tick_type != TickType.TRADE: return        # only using trade bars
                
        elif  k.tick_type == 'TICK_EOF' and not self.strategyStopped:
            self.endTrading = True
            message = f'>{k.timestamp} END OF DATA - TRADING STOPPED ***'
            _logger.info(message)
            self.ParmsDisplay(k)
            self.strategyStopped = True
            self.SqLiteWriteData()
            
        elif k.tick_type != 'TickType.TRADE': return  # backtesting comes in as a string
        
        self.change_variables()

        if k.timestamp < self.start_time:           
            return
            
        if k.timestamp > self.end_time:
            if not self.strategyStopped: 
                self.ClosePosition(k)
                message = f'>{k.timestamp} END OF DAY - TRADING STOPPED ***'
                _logger.info(message)
                self.ParmsDisplay(k)
                if self.sendSmsMsgs: self.SmsSend(self.PortfolioMsg(k, message))
                self.strategyStopped = True
                self.SqLiteWriteData()
                return
            return

        if self.endTrading:
            self.ClosePosition(k)

        if self.strategyStopped:
            self.SqLiteWriteData()
            return

        # Indicators
        # Start ####################################################################################################

        seconds =  (k.timestamp - self.start_time).seconds

        if seconds == self.df_index:          # same bar
            self.df_bar['High'].iloc[seconds] = max(self.df_bar['High'].iloc[seconds], k.price)
            self.df_bar['Low'].iloc[seconds] = min(self.df_bar['Low'].iloc[seconds],  k.price)
            self.df_bar['Close'].iloc[seconds] = k.price
            self.df_bar['Volume'].iloc[seconds] += k.size
        else:                               # new bar
            self.df_bar['Open'].iloc[seconds] = k.price
            self.df_bar['High'].iloc[seconds] = k.price
            self.df_bar['Low'].iloc[seconds] = k.price
            self.df_bar['Close'].iloc[seconds] = k.price
            self.df_bar['Volume'].iloc[seconds] = k.size
            self.df_index = seconds

        df_Close = self.df_bar['Close'].dropna()

        if df_Close.shape[0] < self.df_SecsPerBar:
            return

        # Calculate Indicators
        self.df_SMA = round(talib.SMA(df_Close, timeperiod=self.df_NumOfBars).iloc[-1],2)
        self.df_EMA = round(talib.EMA(df_Close, timeperiod=self.df_NumOfBars).iloc[-1],2)
        self.df_STD = round(talib.STDDEV(df_Close, timeperiod=self.df_NumOfBars).iloc[-1],2)
        self.df_RSI = round(talib.RSI(df_Close, 14).iloc[-1],2)
        self.df_SMA_UpperBand = round(self.df_SMA + (self.df_STD * self.df_StdDev),2)
        self.df_SMA_LowerBand = round(self.df_SMA - (self.df_STD * self.df_StdDev),2)

        # End ######################################################################################################


        # Price slope Trade
        if k.timestamp >= self.rth_start_time:
            if self.priceCtr == 0: 
                self.priceStart = k.price
                self.priceSum = 0.0
            self.priceCtr += 1
            self.priceSum += k.price
            self.priceAvg = self.priceSum / self.priceCtr
            self.priceSlope = round(self.priceAvg - self.priceStart,2)

        # Price slope Day
        if k.timestamp >= self.rth_start_time:
            if self.priceCtrDay == 0: 
                self.priceStartDay = k.price
                self.priceSumDay = 0.0
            self.priceCtrDay += 1
            self.priceSumDay += k.price
            self.priceAvgDay = self.priceSumDay / self.priceCtrDay
            self.priceSlopeDay = round(self.priceAvgDay - self.priceStartDay,2)


        # Still Trading ?
        if k.timestamp < self.start_time: return
        if not self.endTrading:
            if self.totalBuySellCount == -1:
                self.init_dual_time_frame_rule(k)
                self.totalBuySellCount = 0
                return            
            self.dual_time_frame_rule(k)

    def dual_time_frame_rule(self, k):
        self.tickNumber +=1       
        t = k.timestamp
        price = k.price 

        # Open - Close Prices
        if self.priceOpen == 0.0:
            self.priceClose = self.priceOpen = price
        else:
            self.priceClose = price
        self.priceChange = round(self.priceClose - self.priceOpen,2)

        # Take Profit Check
        if self.Max_uPnL_Check(t, k): return

        # Limit Loss Check
        if self.MaxLossCheck(t, k): return

        # Buy - Sell Logic
        if self.currentPosition == 0 and self.df_RSI < self.rsi_over_sold and self.df_EMA < self.df_SMA:# and self.priceSlope < -self.priceSlopeThreshold and price < self.df_SMA_LowerBand:
            self.goShort = True
        if self.currentPosition == 0 and self.df_RSI > self.rsi_over_bought and self.df_EMA > self.df_SMA:# and self.priceSlope > self.priceSlopeThreshold and price > self.df_SMA_UpperBand:
            self.goLong = True

        # Long - Short Algo
        if self.goLong:
            self.goLong = False

            # Calculate short sale
            self.uPnL = -(self.shortSellPrice - price) * self.currentPosition
            if self.currentPosition < 0: self.LogTxt(t, k, '*** SHORT CLOSED ' + str(int(self.uPnL)), True)
            self.longBuyPrice = price
            self.shortSellPrice = price
            self.rPnL += self.uPnL                 
                
            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size = self.orderSize - self.currentPosition
                
            # Commission
            self.totalBuySellCount += 1  
            self.currentPosition = self.orderSize
            commission = abs(self.commissionPerShare * o.order_size)
            self.commissionTotal -= commission
            self.rPnL -= commission

            # Place Order
            self.uPnL = 0.0
            self.max_uPnL = -1000000.0
            self.LogTxt(t, k, '*** LONG PURCHASE ', True)
            if not self.backTestSwt: self.place_order(o)
            if self.sendSmsMsgs: self.SmsSend(self.PortfolioMsg(k, "LONG PURCHASE"))

        # Short Transaction
        if self.goShort:
            self.goShort = False
            
            # Calculate long sale
            self.uPnL = -(self.longBuyPrice - price) * self.currentPosition
            if self.currentPosition > 0: self.LogTxt(t, k, '*** LONG CLOSED ' + str(int(self.uPnL)), True)
            self.longBuyPrice = price
            self.shortSellPrice = price
            self.rPnL += self.uPnL

            o = OrderEvent()
            o.full_symbol = self.symbols[0]
            o.order_type = OrderType.MARKET
            o.order_size = -self.orderSize - self.currentPosition
                
            # Commission
            self.totalBuySellCount += 1 
            self.currentPosition = -self.orderSize
            commission = abs(self.commissionPerShare * o.order_size)
            self.commissionTotal -= commission
            self.rPnL -= commission

            # Place Order
            self.uPnL = 0.0
            self.max_uPnL = -1000000.0
            self.LogTxt(t, k, '*** SHORT PURCHASE ', True)
            if not self.backTestSwt: self.place_order(o)
            if self.sendSmsMsgs: self.SmsSend(self.PortfolioMsg(k, "SHORT PURCHASE"))

        # Holding
        if self.currentPosition == 0:
            self.uPnL = 0.0
            self.LogTxt(t, k, 'NO POSITION ' + str(int(self.uPnL)), False)
        elif self.currentPosition > 0:
            self.uPnL = (price - self.longBuyPrice) * self.currentPosition
            self.LogTxt(t, k, 'HOLDING LONG ' + str(int(self.uPnL)), False)
        elif self.currentPosition < 0:
            self.uPnL = (price - self.shortSellPrice) * self.currentPosition
            self.LogTxt(t, k, 'HOLDING SHORT ' + str(int(self.uPnL)), False)
          
        # SMS 5 min update
        if self.sendSmsMsgs: self.SmsMsgUpdate(k)


class DualTimeFrameStrategyWithGUI(DualTimeFrameStrategy):
    def __init__(self):
        super().__init__()

        # Create the main window
        self.root = tk.Tk()
        self.root.title("Dual Time Frame Strategy")

        # Add a button to show the popup window
        self.button = tk.Button(self.root, text="Change Variables", command=self.change_variables)
        self.button.pack(padx=10, pady=10)

        # Start the main loop
        self.root.mainloop()


class MyGUI:
    def __init__(self, strategy):
        self.strategy = strategy

        # Create a new popup window
        self.popup_window = tk.Toplevel()
        self.popup_window.title("Change Variables")
        self.popup_window.geometry("300x200")

        # Create input fields for each variable
        end_time_label = tk.Label(self.popup_window, text="End Time:")
        end_time_label.grid(row=0, column=0, padx=5, pady=5)
        self.end_time_entry = tk.Entry(self.popup_window)
        self.end_time_entry.grid(row=0, column=1, padx=5, pady=5)

        long_buy_price_label = tk.Label(self.popup_window, text="Long Buy Price:")
        long_buy_price_label.grid(row=1, column=0, padx=5, pady=5)
        self.long_buy_price_entry = tk.Entry(self.popup_window)
        self.long_buy_price_entry.grid(row=1, column=1, padx=5, pady=5)

        tick_number_label = tk.Label(self.popup_window, text="Tick Number:")
        tick_number_label.grid(row=2, column=0, padx=5, pady=5)
        self.tick_number_entry = tk.Entry(self.popup_window)
        self.tick_number_entry.grid(row=2, column=1, padx=5, pady=5)

        back_test_swt_label = tk.Label(self.popup_window, text="Back Test Switch:")
        back_test_swt_label.grid(row=3, column=0, padx=5, pady=5)
        self.back_test_swt_entry = tk.Entry(self.popup_window)
        self.back_test_swt_entry.grid(row=3, column=1, padx=5, pady=5)

        # Add a submit button that updates the variables and closes the window
        submit_button = tk.Button(self.popup_window, text="Submit", command=lambda:
            self.submit_button_callback())
        submit_button.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # Make sure the window stays on top
        self.popup_window.attributes('-topmost', True)

    def submit_button_callback(self):
        # Set the new values for the variables
        self.strategy.update_variables(end_time=self.end_time_entry.get(),
                                        long_buy_price=float(self.long_buy_price_entry.get()),
                                        tick_number=int(self.tick_number_entry.get()),
                                        back_test_swt=bool(self.back_test_swt_entry.get()))

        # Close the popup window
        self.popup_window.destroy()


# Create an instance of the GUI
gui = MyGUI('strategy')
