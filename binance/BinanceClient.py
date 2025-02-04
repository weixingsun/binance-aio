import asyncio
import aiohttp
import hmac
import hashlib
import ssl
import logging
import datetime
import json
from typing import List, Optional

from binance.Pair import Pair
from binance.subscriptions import Subscription, SubscriptionMgr
from binance import enums
from binance.Timer import Timer
from binance.BinanceException import BinanceException

LOG = logging.getLogger(__name__)

class BinanceClient(object):
	

	def __init__(self, rest_uri = "https://api.binance.com/api/v3/", certificate_path : str = None, 
		     api_key : str = None, sec_key : str = None, api_trace_log : bool = False) -> None:
		self.api_key = api_key
		self.sec_key = sec_key
		self.api_trace_log = api_trace_log
		self.REST_API_URI = rest_uri
		self.rest_session = None
		self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
		self.ssl_context.load_verify_locations(certificate_path)

		self.subscription_sets = []

	async def ping(self) -> dict:
		return await self._create_get("ping")

	async def get_exchange_info(self) -> dict:
		return await self._create_get("exchangeInfo")

	async def get_time(self) -> dict:
		return await self._create_get("time")

	async def get_orderbook(self, pair : Pair, limit : enums.DepthLimit = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
		})

		if limit:
			params['limit'] = limit.value

		return await self._create_get("depth", params = params)

	async def get_trades(self, pair : Pair, limit : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
			"limit": limit
		})

		return await self._create_get("trades", params = params)

	async def get_historical_trades(self, pair : Pair, limit : int = None, from_id : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
			"limit": limit,
			"fromId": from_id
		})

		return await self._create_get("historicalTrades", params = params, headers = self._get_header_api_key())

	async def get_aggregate_trades(self, pair : Pair, limit : int = None, from_id : int = None, start_tmstmp_ms : int = None, end_tmstmp_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
			"limit": limit,
			"fromId": from_id,
			"startTime": start_tmstmp_ms,
			"endTime": end_tmstmp_ms
		})

		return await self._create_get("aggTrades", params = params)

	async def get_candelsticks(self, pair : Pair, limit : int = None, interval : enums.CandelstickInterval = None, start_tmstmp_ms : int = None, end_tmstmp_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
			"limit": limit,
			"startTime": start_tmstmp_ms,
			"endTime": end_tmstmp_ms
		})

		if interval:
			params['interval'] = interval.value

		return await self._create_get("klines", params = params)

	async def get_average_price(self, pair : Pair) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair
		})

		return await self._create_get("avgPrice", params = params)

	async def get_24h_price_ticker(self, pair : Pair = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
		})

		return await self._create_get("ticker/24hr", params = params)

	async def get_price_ticker(self, pair : Pair = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
		})

		return await self._create_get("ticker/price", params = params)

	async def get_best_orderbook_ticker(self, pair : Optional[Pair] = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
		})

		return await self._create_get("ticker/bookTicker", headers = self._get_header_api_key(), params = params)

	async def create_order(self, pair : Pair, side : enums.OrderSide, type : enums.OrderType,
	                             quantity : str,
	                             price : str = None,
								 stop_price: str = None,
	                             quote_order_quantity: str = None,
	                             time_in_force: enums.TimeInForce = None,
	                             new_client_order_id : str = None,
	                             iceberg_quantity : str = None,
	                             new_order_response_type : enums.OrderResponseType = None,
	                             recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"side": side.value,
			"type": type.value,
			"quantity": quantity,
			"quoteOrderQty": quote_order_quantity,
			"price": price,
			"stopPrice": stop_price,
			"newClientOrderId": new_client_order_id,
			"icebergQty": iceberg_quantity,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		if time_in_force:
			params['timeInForce'] = time_in_force.value

		if new_order_response_type:
			params['newOrderRespType'] = new_order_response_type.value

		return await self._create_post("order", params = params, headers = self._get_header_api_key(), signed = True)

	async def create_test_order(self, pair : Pair, side : enums.OrderSide, type : enums.OrderType,
	                             quantity : str,
	                             price : str = None,
								 stop_price: str = None,
	                             quote_order_quantity: str = None,
	                             time_in_force: enums.TimeInForce = None,
	                             new_client_order_id : str = None,
	                             iceberg_quantity : str = None,
	                             new_order_response_type : enums.OrderResponseType = None,
	                             recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"side": side.value,
			"type": type.value,
			"quantity": quantity,
			"quoteOrderQty": quote_order_quantity,
			"price": price,
			"stopPrice": stop_price,
			"newClientOrderId": new_client_order_id,
			"icebergQty": iceberg_quantity,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		if time_in_force:
			params['timeInForce'] = time_in_force.value

		if new_order_response_type:
			params['newOrderRespType'] = new_order_response_type.value

		return await self._create_post("order/test", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_order(self, pair : Pair, order_id : int = None, orig_client_order_id : int = None, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"orderId": order_id,
			"origClientOrderId": orig_client_order_id,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("order", params = params, headers = self._get_header_api_key(), signed = True)

	async def cancel_order(self, pair : Pair, order_id : str = None, orig_client_order_id : str = None,
	                       new_client_order_id : str = None, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"orderId": order_id,
			"origClientOrderId": orig_client_order_id,
			"newClientOrderId": new_client_order_id,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_delete("order", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_open_orders(self, pair : Pair = None, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("openOrders", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_all_orders(self, pair : Pair, order_id : int = None, limit : int = None, start_tmstmp_ms : int = None, end_tmstmp_ms : int = None, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"orderId": order_id,
			"startTime": start_tmstmp_ms,
			"endTime": end_tmstmp_ms,
			"limit": limit,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("allOrders", params = params, headers = self._get_header_api_key(), signed = True)

	async def create_oco_order(self, pair : Pair, side : enums.OrderSide,
	                           quantity : str,
	                           price: str,
	                           stop_price: str,
	                           limit_client_order_id: str = None,
	                           list_client_order_id: str = None,
	                           limit_iceberg_quantity: str = None,
	                           stop_client_order_id: str = None,
	                           stop_limit_price: str = None,
	                           stop_iceberg_quantity: str = None,
	                           stop_limit_time_in_force: enums.TimeInForce = None,
	                           new_order_response_type : enums.OrderResponseType = None,
	                           recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"side": side.value,
			"quantity": quantity,
			"listClientOrderId": list_client_order_id,
			"limitClientOrderId": limit_client_order_id,
			"price": price,
			"stopClientOrderId": stop_client_order_id,
			"stopPrice": stop_price,
			"stopLimitPrice": stop_limit_price,
			"stopIcebergQty": stop_iceberg_quantity,
			"limitIcebergQty": limit_iceberg_quantity,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		if stop_limit_time_in_force:
			params['stopLimitTimeInForce'] = stop_limit_time_in_force.value

		if new_order_response_type:
			params['newOrderRespType'] = new_order_response_type.value

		return await self._create_post("order/oco", params = params, headers = self._get_header_api_key(), signed = True)

	async def cancel_oco_order(self, pair : Pair, order_list_id : str = None, list_client_order_id : str = None,
	                       new_client_order_id : str = None, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": str(pair),
			"orderListId": order_list_id,
			"listClientOrderId": list_client_order_id,
			"newClientOrderId": new_client_order_id,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_delete("orderList", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_oco_order(self, order_list_id : int = None, orig_client_order_id : int = None, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"orderListId": order_list_id,
			"origClientOrderId": orig_client_order_id,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("orderList", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_all_oco_orders(self, from_id : int = None, limit : int = None, start_tmstmp_ms : int = None, end_tmstmp_ms : int = None, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"fromId": from_id,
			"startTime": start_tmstmp_ms,
			"endTime": end_tmstmp_ms,
			"limit": limit,
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("allOrderList", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_open_oco_orders(self, recv_window_ms : int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("openOrderList", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_account(self, recv_window_ms: Optional[int] = None) -> dict:
		params = BinanceClient._clean_request_params({
			"recvWindow": recv_window_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("account", headers = self._get_header_api_key(), params = params, signed = True)

	async def get_account_trades(self, pair: Pair, limit: int = None, from_id: int = None,
	                               start_tmstmp_ms: int = None, end_tmstmp_ms: int = None) -> dict:
		params = BinanceClient._clean_request_params({
			"symbol": pair,
			"limit": limit,
			"fromId": from_id,
			"startTime": start_tmstmp_ms,
			"endTime": end_tmstmp_ms,
			"timestamp": self._get_current_timestamp_ms()
		})

		return await self._create_get("myTrades", params = params, headers = self._get_header_api_key(), signed = True)

	async def get_listen_key(self):
		return await self._create_post("userDataStream", headers = self._get_header_api_key())

	def compose_subscriptions(self, subscriptions : List[Subscription]) -> None:
		self.subscription_sets.append(subscriptions)

	async def start_subscriptions(self) -> None:
		if len(self.subscription_sets):
			done, pending = await asyncio.wait(
				[asyncio.create_task(SubscriptionMgr(subscriptions, self.api_key, self.ssl_context).run()) for subscriptions in self.subscription_sets],
				return_when = asyncio.FIRST_EXCEPTION
			)
			for task in done:
				try:
					task.result()
				except Exception as e:
					LOG.exception(f"Unrecoverable exception occurred while processing messages: {e}")
					LOG.info("All websockets scheduled for shutdown")
					for task in pending:
						if not task.cancelled():
							task.cancel()
		else:
			raise Exception("ERROR: There are no subscriptions to be started.")

	async def close(self) -> None:
		session = self._get_rest_session()
		if session is not None:
			await session.close()

	async def _create_get(self, resource : str, params : dict = None, headers : dict = None, signed : bool = False) -> dict:
		return await self._create_rest_call(enums.RestCallType.GET, resource, None, params, headers, signed)

	async def _create_post(self, resource : str, data : dict = None, params : dict = None, headers : dict = None, signed : bool = False) -> dict:
		return await self._create_rest_call(enums.RestCallType.POST, resource, data, params, headers, signed)

	async def _create_delete(self, resource : str, params : dict = None, headers : dict = None, signed : bool = False) -> dict:
		return await self._create_rest_call(enums.RestCallType.DELETE, resource, None, params, headers, signed)

	async def _create_put(self, resource : str, params : dict = None, headers : dict = None, signed : bool = False) -> dict:
		return await self._create_rest_call(enums.RestCallType.PUT, resource, None, params, headers, signed)

	async def _create_rest_call(self, rest_call_type : enums.RestCallType, resource : str, data : dict = None, params : dict = None, headers : dict = None, signed : bool = False) -> dict:
		with Timer('RestCall'):
			# add signature into parameters
			if signed:
				params = {} if params is None else params
				params['signature'] = self._get_signature(params, data)

			if rest_call_type == enums.RestCallType.GET:
				rest_call = self._get_rest_session().get(self.REST_API_URI + resource, json = data, params = params, headers = headers, ssl = self.ssl_context)
			elif rest_call_type == enums.RestCallType.POST:
				rest_call = self._get_rest_session().post(self.REST_API_URI + resource, json = data, params = params, headers = headers, ssl = self.ssl_context)
			elif rest_call_type == enums.RestCallType.DELETE:
				rest_call = self._get_rest_session().delete(self.REST_API_URI + resource, json = data, params = params, headers = headers, ssl = self.ssl_context)
			elif rest_call_type == enums.RestCallType.PUT:
				rest_call = self._get_rest_session().put(self.REST_API_URI + resource, json = data, params = params, headers = headers, ssl = self.ssl_context)
			else:
				raise Exception(f"Unsupported REST call type {rest_call_type}.")

			LOG.debug(f"> rest type [{rest_call_type.name}], resource [{resource}], params [{params}], headers [{headers}], data [{data}]")
			async with rest_call as response:
				status_code = response.status
				response_body = await response.text()

				LOG.debug(f"<: status [{status_code}], response [{response_body}]")

				if str(status_code)[0] != '2':
					raise BinanceException(f"<: status [{status_code}], response [{response_body}]")

				if len(response_body) > 0:
					response_body = json.loads(response_body)

				return {
					"status_code": status_code,
					"response": response_body
				}

	def _get_rest_session(self) -> aiohttp.ClientSession:
		if self.rest_session is not None:
			return self.rest_session

		if self.api_trace_log:
			trace_config = aiohttp.TraceConfig()
			trace_config.on_request_start.append(BinanceClient._on_request_start)
			trace_config.on_request_end.append(BinanceClient._on_request_end)
			trace_configs = [trace_config]
		else:
			trace_configs = None

		self.rest_session = aiohttp.ClientSession(trace_configs=trace_configs)

		return self.rest_session

	def _get_header_api_key(self):
		header = {
			'Accept': 'application/json',
			"X-MBX-APIKEY": self.api_key
		}

		return header

	@staticmethod
	def _clean_request_params(params : dict) -> dict:
		res = {}
		for key, value in params.items():
			if value is not None:
				res[key] = str(value)

		return res

	async def _on_request_start(session, trace_config_ctx, params) -> None:
		LOG.debug(f"> Context: {trace_config_ctx}")
		LOG.debug(f"> Params: {params}")

	async def _on_request_end(session, trace_config_ctx, params) -> None:
		LOG.debug(f"< Context: {trace_config_ctx}")
		LOG.debug(f"< Params: {params}")

	@staticmethod
	def _get_current_timestamp_ms() -> int:
		return int(datetime.datetime.now(tz = datetime.timezone.utc).timestamp() * 1000)

	def _get_signature(self, params : dict, data : dict) -> str:
		params_string = ""
		data_string = ""

		if params is not None:
			params_string = '&'.join([f"{key}={val}" for key, val in params.items()])

		if data is not None:
			data_string = '&'.join(["{}={}".format(param[0], param[1]) for param in data])

		m = hmac.new(self.sec_key.encode('utf-8'), (params_string+data_string).encode('utf-8'), hashlib.sha256)
		return m.hexdigest()
