import asyncio
import websockets
import json
import time
from gmo_order import send_post_only_limit_order, cancel_all_positions

latest_bid = None
latest_ask = None
current_buy_order_id = None
current_sell_order_id = None

last_buy_price = None
last_sell_price = None
last_order_time = 0

ORDER_INTERVAL = 1  # 最小発注間隔（秒）
SPREAD_THRESHOLD = 0.002  # 最小スプレッド（＝0.2%）
MAX_RETRIES = 5  # 最大再接続回数
RETRY_DELAY = 5  # 再接続待機時間（秒）

async def order_loop():
    global current_buy_order_id, current_sell_order_id
    global last_buy_price, last_sell_price, last_order_time

    while True:
        if latest_bid is None or latest_ask is None:
            await asyncio.sleep(0.1)
            continue

        # スプレッドが一定以上であることを確認
        spread = latest_ask - latest_bid
        spread_pct = spread / latest_bid

        if spread_pct < SPREAD_THRESHOLD:
            print(f"❌ スプレッドが狭い: {spread_pct:.4%} < {SPREAD_THRESHOLD*100:.1f}% → 発注スキップ")
            await asyncio.sleep(1)
            continue

        maker_buy_price = round(latest_bid + 0.001, 3)
        maker_sell_price = round(latest_ask - 0.001, 3)

        now = time.time()
        price_changed = (
            maker_buy_price != last_buy_price or
            maker_sell_price != last_sell_price
        )
        enough_time_passed = (now - last_order_time) >= ORDER_INTERVAL

         # 売りはスプレッド関係なく出す、買いだけ判定する
        should_buy = spread_pct >= SPREAD_THRESHOLD
        should_send = price_changed and enough_time_passed

        if should_send:
            print(f"✅ 発注判定 → Buy条件: {should_buy}, Spread: {spread_pct:.4%}, Buy: {maker_buy_price}, Sell: {maker_sell_price}")
            cancel_all_positions("DOGE")

            if should_buy:
                current_buy_order_id = send_post_only_limit_order("DOGE", "BUY", 10, maker_buy_price)
                last_buy_price = maker_buy_price
            else:
                print(f"❌ 買いスキップ → スプレッドが狭い: {spread_pct:.4%} < {SPREAD_THRESHOLD*100:.1f}%")

            current_sell_order_id = send_post_only_limit_order("DOGE", "SELL", 10, maker_sell_price)
            last_sell_price = maker_sell_price
            last_order_time = now
        else:
            await asyncio.sleep(0.5)

async def listen_to_orderbook():
    global latest_bid, latest_ask
    uri = "wss://api.coin.z.com/ws/public/v1"
    retry_count = 0

    while retry_count < MAX_RETRIES:
        try:
            async with websockets.connect(
                uri,
                ping_interval=20,  # 20秒ごとにping
                ping_timeout=10,   # pingのタイムアウトは10秒
                close_timeout=10   # クローズのタイムアウトは10秒
            ) as websocket:
                subscribe_msg = {
                    "command": "subscribe",
                    "channel": "orderbooks",
                    "symbol": "DOGE"
                }
                await websocket.send(json.dumps(subscribe_msg))
                print("✅ Subscribed to DOGE orderbooks")
                retry_count = 0  # 接続成功したらリトライカウントをリセット

                while True:
                    try:
                        response = await websocket.recv()
                        data = json.loads(response)

                        if "bids" in data and "asks" in data:
                            latest_bid = float(data["bids"][0]["price"])
                            latest_ask = float(data["asks"][0]["price"])
                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"⚠️ WebSocket接続が切断されました: {e}")
                        break
                    except Exception as e:
                        print(f"⚠️ 予期せぬエラーが発生しました: {e}")
                        continue

        except Exception as e:
            retry_count += 1
            print(f"⚠️ 接続エラー ({retry_count}/{MAX_RETRIES}): {e}")
            if retry_count < MAX_RETRIES:
                print(f"⏳ {RETRY_DELAY}秒後に再接続を試みます...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                print("❌ 最大再接続回数に達しました。プログラムを終了します。")
                raise

async def main():
    await asyncio.gather(
        listen_to_orderbook(),
        order_loop()
    )

asyncio.run(main())
