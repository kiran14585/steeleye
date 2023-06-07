from typing import List
from fastapi import FastAPI,HTTPException,Query
from pydantic import BaseModel, Field
import sqlite3
import datetime as dt


conn = sqlite3.connect("trades.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM trades")
rows = cursor.fetchall()



class TradeDetails(BaseModel):
    buySellIndicator: str = Field(description="A value of BUY for buys, SELL for sells.")
    price: float = Field(description="The price of the Trade.")
    quantity: int = Field(description="The amount of units traded.")


class Trade(BaseModel):
    assetClass: str = Field(alias="asset_class", default=None, description="The asset class of the instrument traded. E.g. Bond, Equity, FX...etc")
    counterparty: str = Field(default=None, description="The counterparty the trade was executed with. May not always be available")
    instrumentId: str = Field(alias="instrument_id", description="The ISIN/ID of the instrument traded. E.g. TSLA, AAPL, AMZN...etc")
    instrumentName: str = Field(alias="instrument_name", description="The name of the instrument traded.")
    tradeDateTime: dt.datetime = Field(alias="trade_date_time", description="The date-time the Trade was executed")
    tradeDetails: TradeDetails = Field(alias="trade_details", description="The details of the trade, i.e. price, quantity")
    tradeId: str = Field(alias="trade_id", default=None, description="The unique ID of the trade")
    trader: str = Field(alias="trader", description="The name of the Trader")

    # Optional filtering parameters
    assetClass: str = Field(default=None, description="Asset class of the trade.")
    end: dt.datetime = Field(default=None, description="The maximum date for the tradeDateTime field.")
    maxPrice: float = Field(default=None, description="The maximum value for the tradeDetails.price field.")
    minPrice: float = Field(default=None, description="The minimum value for the tradeDetails.price field.")
    start: dt.datetime = Field(default=None, description="The minimum date for the tradeDateTime field.")
    tradeType: str = Field(default=None, description="The tradeDetails.buySellIndicator is a BUY or SELL")


app = FastAPI()

# Sample data
trades = []
for row in rows:
    trade = Trade(
        asset_class=row[0],
        counterparty=row[1],
        instrument_id=row[2],
        instrument_name=row[3],
        trade_date_time=dt.datetime.fromisoformat(row[4]),
        trade_details=TradeDetails(
            buySellIndicator=row[5],
            price=float(row[6]),
            quantity=int(row[7])
        ),
        trade_id=row[8],
        trader=row[9],
        assetClass=row[10],
        end=dt.datetime.fromisoformat(row[11]),
        maxPrice=float(row[12]),
        minPrice=float(row[13]),
        start=dt.datetime.fromisoformat(row[14]),
        tradeType=row[15]
    )
    trades.append(trade)




@app.get("/trades", response_model=List[Trade])
async def get_trades(
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0),
    counterparty: str = Query(default=None),
    instrument_id: str = Query(default=None, alias="instrumentId"),
    instrument_name: str = Query(default=None, alias="instrumentName"),
    trader: str = Query(default=None),
    asset_class: str = Query(default=None),
    start: dt.datetime = Query(default=None),
    end: dt.datetime = Query(default=None),
    min_price: float = Query(default=None, alias="minPrice"),
    max_price: float = Query(default=None, alias="maxPrice"),
    trade_type: str = Query(default=None, alias="tradeType"),
    sort_by: str = Query(default=None, regex=r"^(price|tradeId)$"),
    sort_order: str = Query("asc", regex=r"^(asc|desc)$")
):
    filtered_trades = trades

    # Apply filters
    if counterparty:
        filtered_trades = [trade for trade in filtered_trades if trade.counterparty == counterparty]
    if instrument_id:
        filtered_trades = [trade for trade in filtered_trades if trade.instrumentId == instrument_id]
    if instrument_name:
        filtered_trades = [trade for trade in filtered_trades if trade.instrumentName == instrument_name]
    if trader:
        filtered_trades = [trade for trade in filtered_trades if trade.trader == trader]
    if asset_class:
        filtered_trades = [trade for trade in filtered_trades if trade.assetClass == asset_class]
    if start:
        filtered_trades = [trade for trade in filtered_trades if trade.tradeDateTime >= start]
    if end:
        filtered_trades = [trade for trade in filtered_trades if trade.tradeDateTime <= end]
    if min_price:
        filtered_trades = [trade for trade in filtered_trades if trade.tradeDetails.price >= min_price]
    if max_price:
        filtered_trades = [trade for trade in filtered_trades if trade.tradeDetails.price <= max_price]
    if trade_type:
        filtered_trades = [trade for trade in filtered_trades if trade.tradeDetails.buySellIndicator == trade_type]

    # Apply sorting
    if sort_by:
        reverse = sort_order.lower() == "desc"
        if sort_by == "tradeId":
            filtered_trades = sorted(filtered_trades, key=lambda x: x.tradeId, reverse=reverse)
        else:
            filtered_trades = sorted(filtered_trades, key=lambda x: getattr(x.tradeDetails, sort_by), reverse=reverse)

    # Apply pagination
    start_index = (page - 1) * limit
    end_index = start_index + limit
    paginated_trades = filtered_trades[start_index:end_index]

    return paginated_trades



# Retrieve a single trade by ID
@app.get("/trades/{trade_id}", response_model=Trade)
async def get_trade_by_id(trade_id: str):
    for trade in trades:
        if trade.tradeId == trade_id:
            return trade
    raise HTTPException(status_code=404, detail="Trade not found")