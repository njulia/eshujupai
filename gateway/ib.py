import collections
import inspect
import logging
from enum import Enum
from contextlib import contextmanager

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import *
from ibapi.order import *
from ibapi.utils import iswrapper


log = logging.getLogger(__name__)


class Side(Enum):
    BUY='BUY'
    SELL='SELL'


# ! [socket_declare]
class TestClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        # ! [socket_declare]

        # how many times a method is called to see test coverage
        self.clntMeth2callCount = collections.defaultdict(int)
        self.clntMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nReq = collections.defaultdict(int)
        self.setupDetectReqId()

    def countReqId(self, methName, fn):
        def countReqId_(*args, **kwargs):
            self.clntMeth2callCount[methName] += 1
            idx = self.clntMeth2reqIdIdx[methName]
            if idx >= 0:
                sign = -1 if 'cancel' in methName else 1
                self.reqId2nReq[sign * args[idx]] += 1
            return fn(*args, **kwargs)

        return countReqId_

    def setupDetectReqId(self):

        methods = inspect.getmembers(EClient, inspect.isfunction)
        for (methName, meth) in methods:
            if methName != "send_msg":
                # don't screw up the nice automated logging in the send_msg()
                self.clntMeth2callCount[methName] = 0
                # logging.debug("meth %s", name)
                sig = inspect.signature(meth)
                for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                    (paramName, param) = pnameNparam # @UnusedVariable
                    if paramName == "reqId":
                        self.clntMeth2reqIdIdx[methName] = idx

                setattr(TestClient, methName, self.countReqId(methName, meth))

                # print("TestClient.clntMeth2reqIdIdx", self.clntMeth2reqIdIdx)


# ! [ewrapperimpl]
class TestWrapper(EWrapper):
    # ! [ewrapperimpl]
    def __init__(self):
        EWrapper.__init__(self)

        self.wrapMeth2callCount = collections.defaultdict(int)
        self.wrapMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nAns = collections.defaultdict(int)
        self.setupDetectWrapperReqId()

    # TODO: see how to factor this out !!

    def countWrapReqId(self, methName, fn):
        def countWrapReqId_(*args, **kwargs):
            self.wrapMeth2callCount[methName] += 1
            idx = self.wrapMeth2reqIdIdx[methName]
            if idx >= 0:
                self.reqId2nAns[args[idx]] += 1
            return fn(*args, **kwargs)

        return countWrapReqId_

    def setupDetectWrapperReqId(self):

        methods = inspect.getmembers(EWrapper, inspect.isfunction)
        for (methName, meth) in methods:
            self.wrapMeth2callCount[methName] = 0
            # logging.debug("meth %s", name)
            sig = inspect.signature(meth)
            for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                (paramName, param) = pnameNparam # @UnusedVariable
                # we want to count the errors as 'error' not 'answer'
                if 'error' not in methName and paramName == "reqId":
                    self.wrapMeth2reqIdIdx[methName] = idx

            setattr(TestWrapper, methName, self.countWrapReqId(methName, meth))

            # print("TestClient.wrapMeth2reqIdIdx", self.wrapMeth2reqIdIdx)



class IBApp(TestWrapper, TestClient):
    def __init__(self):

        TestWrapper.__init__(self)
        # self.wrapMeth2callCount = collections.defaultdict(int)
        # self.wrapMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        # self.reqId2nAns = collections.defaultdict(int)
        self.setupDetectWrapperReqId()

        TestClient.__init__(self, wrapper=self)
        # ! [socket_declare]
        # how many times a method is called to see test coverage
        # self.clntMeth2callCount = collections.defaultdict(int)
        # self.clntMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        # self.reqId2nReq = collections.defaultdict(int)
        self.setupDetectReqId()

        # ! [socket_init]
        self.nKeybInt = 0
        self.started = False
        self.permId2ord = {}
        self.reqId2nErr = collections.defaultdict(int)
        self.globalCancelOnly = False
        self.simplePlaceOid = None
        self.nextValidOrderId = 0


    @contextmanager
    def connect(self, *args, **kwargs):
        try:
            conn = self.connect(*args, **kwargs)
            yield conn
        finally:
            self.disconnect()


    @iswrapper
    # ! [connectack]
    def connectAck(self):
        if self.asynchronous:
            self.startApi()

    # ! [connectack]


    @iswrapper
    # ! [nextvalidid]
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        print("NextValidId:", orderId)
    # ! [nextvalidid]

        # # we can start now
        # self.start()


    def next_order_id(self):
        id = self.nextValidOrderId
        self.nextValidOrderId += 1
        return id


    @staticmethod
    def get_action(action):
        if action == 1:
            return 'BUY'
        elif action == -1:
            return 'SELL'
        else:
            raise ValueError(f'Wrong action: {action}, Only BUY or SELL allowed')


    @staticmethod
    def get_opposite_action(action):
        if action == 1:
            return 'SELL'
        elif action == -1:
            return 'BUY'
        else:
            raise ValueError(f'Wrong action: {action}, Only BUY or SELL allowed')


    def place_order(self, ticker:str, action:int, qty:float, qty_adjusted=None, limit_price:float=None, take_profit:float=None, stop_loss:float=None):
        # Set Contract inforation
        con = Contract()
        con.symbol = ticker
        con.secType = "STK"
        con.currency = "USD"
        con.exchange = "SMART"

        bracket_orders = []
        # This will be our main or "parent" order
        parent = Order()
        parent.orderId = parent_order_id = self.next_order_id()
        parent.action = self.get_action(action)
        parent.orderType = "LMT"
        parent.tif = "DAY"
        parent.totalQuantity = qty_adjusted
        parent.lmtPrice = limit_price
        # The parent and children orders will need this attribute set to False to prevent accidental executions.
        # The LAST CHILD will have it set to True,
        parent.transmit = False
        bracket_orders.append(parent)

        if take_profit is not None:
            takeProfit = Order()
            takeProfit.orderId = self.next_order_id()
            takeProfit.action = self.get_opposite_action(action)
            takeProfit.orderType = "LMT"
            takeProfit.tif = "GTC"
            takeProfit.totalQuantity = qty
            takeProfit.lmtPrice = take_profit
            takeProfit.parentId = parent_order_id
            takeProfit.transmit = False
            bracket_orders.append(takeProfit)

        if stop_loss is not None:
            stopLoss = Order()
            stopLoss.orderId = self.next_order_id()
            stopLoss.action = self.get_opposite_action(action)
            stopLoss.orderType = "STP LMT"
            stopLoss.tif = "GTC"
            # Stop trigger price
            stopLoss.totalQuantity = qty
            stopLoss.auxPrice = stop_loss
            stopLoss.lmtPrice = stop_loss
            stopLoss.parentId = parent_order_id
            # In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True
            # to activate all its predecessors
            stopLoss.transmit = True
            bracket_orders.append(stopLoss)

        for order in bracket_orders:
            if self.placeOrder(order.orderId, con, order) == 0:
                log.error(f'Failed to send order {con}: {order}')
            print(f'addd-Place order {con}: {order}')
            log.info(f'Place order {con}: {order}')


    def update_and_new(self, ticker:str, action:int, qty:float, limit_price, take_profit, stop_loss):
        if action == 0:
            log.info(f'{ticker}: NO signal')
            return

        # positions = self.positionMulti()
        # for position in positions:
        #     if position.contract.symbol == ticker:
        #         pass
                # if (position_qty > 0 and action == 'SELL') or (position_qty < 0 and action == 'BUY'):
                #     # close the existing position
                #     close_position = Order()
                #     close_position.orderId = self.next_order_id()
                #     close_position.action = 'SELL' if position_qty > 0 else 'BUY'
                #     close_position.orderType = 'LMT'
                #     close_position.totalQuantity = position_qty
                #     close_position.lmtPrice = limit_price
                #     close_position.transmit = False
                # elif (position_qty > 0 and action == 'BUY') or (position_qty < 0 and action == 'SELL'):

                # if (position_qty > 0 and action == 'SELL') or (position_qty < 0 and action == 'BUY'):
                #     qty_adjusted = position_qty + qty
                # elif (position_qty > 0 and action == 'BUY') or (position_qty < 0 and action == 'SELL'):
                #     # todo: get the orderid of existing position
                #     if qty > position_qty:
                #         qty_adjusted = qty - position_qty
                #     else:
                #         qty_adjusted = 0
                #         qty = position_qty

        self.place_order(ticker, action, qty=qty, qty_adjusted=qty,
                         limit_price=limit_price, take_profit=take_profit, stop_loss=stop_loss)


    def cancel_position(self, tickers=[]):
        if tickers.lower() == 'all':
            self.cancelPositions()
            log.info('Cancel all positions')

        # todo: cancel specific position with ticker in the parameter tickers



def main():

    app = IBApp()
    app.run()

    app.get_open_orders()


if __name__ == "__main__":
    main()