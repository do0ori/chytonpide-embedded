"""
server_tcp - TCP Device Server

ESP32 디바이스와 외부 제어 클라이언트를 위한 TCP 서버.
프로토콜: newline-delimited JSON.
"""

import asyncio
import json
import logging
from datetime import datetime

HOST = "0.0.0.0"
PORT = 9000
PING_INTERVAL = 30  # seconds
PONG_TIMEOUT = 60  # seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("server_tcp")

# --- State ---

# serial -> StreamWriter (접속 중인 디바이스)
device_connections: dict[str, asyncio.StreamWriter] = {}

# serial -> {"is_led_on": bool, "face": str}
device_states: dict[str, dict] = {}

# serial -> last pong timestamp (monotonic)
device_last_pong: dict[str, float] = {}

DEFAULT_STATE = {"is_led_on": False, "face": "NEUTRAL"}


# --- Helpers ---

async def send_json(writer: asyncio.StreamWriter, data: dict) -> bool:
    """Send a JSON message terminated by newline. Returns False on failure."""
    try:
        msg = json.dumps(data, separators=(",", ":")) + "\n"
        writer.write(msg.encode())
        await writer.drain()
        return True
    except (ConnectionError, OSError):
        return False


def get_state(serial: str) -> dict:
    return device_states.setdefault(serial, {**DEFAULT_STATE})


# --- Message handlers ---

async def handle_hello(data: dict, writer: asyncio.StreamWriter) -> str | None:
    """Register device connection. Returns serial on success."""
    serial = data.get("serial")
    if not serial or not isinstance(serial, str):
        await send_json(writer, {"type": "error", "message": "missing serial"})
        return None

    # 기존 연결이 있으면 정리
    old_writer = device_connections.get(serial)
    if old_writer and old_writer is not writer:
        old_writer.close()

    device_connections[serial] = writer
    device_last_pong[serial] = asyncio.get_event_loop().time()

    state = get_state(serial)
    await send_json(writer, {
        "type": "hello_ack",
        "is_led_on": state["is_led_on"],
        "face": state["face"],
    })
    log.info("Device connected: %s", serial)
    return serial


async def handle_sensor_data(data: dict, writer: asyncio.StreamWriter):
    serial = data.get("serial", "?")
    temp = data.get("temperature")
    hum = data.get("humidity")
    illu = data.get("illuminance", 0)

    log.info(
        "Sensor [%s] temp=%.2f hum=%.2f illu=%s",
        serial, temp or 0, hum or 0, illu,
    )
    await send_json(writer, {"type": "ack"})


async def handle_set_device(data: dict, writer: asyncio.StreamWriter):
    serial = data.get("serial")
    if not serial:
        await send_json(writer, {"type": "error", "message": "missing serial"})
        return

    state = get_state(serial)
    update: dict = {}

    if "is_led_on" in data:
        val = data["is_led_on"]
        if isinstance(val, str):
            val = val.lower() in ("true", "1", "on", "yes")
        state["is_led_on"] = bool(val)
        update["is_led_on"] = state["is_led_on"]

    if "face" in data:
        state["face"] = str(data["face"]).upper()
        update["face"] = state["face"]

    if not update:
        await send_json(writer, {"type": "error", "message": "no fields to update"})
        return

    log.info("set_device [%s] %s", serial, update)

    # 디바이스가 접속 중이면 push
    dev_writer = device_connections.get(serial)
    if dev_writer:
        await send_json(dev_writer, {"type": "state_update", **update})

    await send_json(writer, {"type": "ack"})


async def handle_pong(serial: str | None):
    if serial:
        device_last_pong[serial] = asyncio.get_event_loop().time()


# --- Connection handler ---

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    log.info("New connection from %s", addr)

    serial: str | None = None  # set after hello

    try:
        while True:
            line = await reader.readline()
            if not line:
                break  # EOF

            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                await send_json(writer, {"type": "error", "message": "invalid json"})
                continue

            msg_type = data.get("type")

            if msg_type == "hello":
                serial = await handle_hello(data, writer)
            elif msg_type == "sensor_data":
                await handle_sensor_data(data, writer)
            elif msg_type == "set_device":
                await handle_set_device(data, writer)
            elif msg_type == "pong":
                await handle_pong(serial)
            else:
                await send_json(writer, {"type": "error", "message": f"unknown type: {msg_type}"})

    except (ConnectionError, OSError):
        pass
    finally:
        # cleanup
        if serial and device_connections.get(serial) is writer:
            del device_connections[serial]
            device_last_pong.pop(serial, None)
            log.info("Device disconnected: %s", serial)
        writer.close()
        log.info("Connection closed: %s", addr)


# --- Ping / timeout task ---

async def ping_loop():
    """Periodically ping devices and drop unresponsive ones."""
    while True:
        await asyncio.sleep(PING_INTERVAL)
        now = asyncio.get_event_loop().time()

        stale: list[str] = []
        for serial, writer in list(device_connections.items()):
            last = device_last_pong.get(serial, 0)
            if now - last > PONG_TIMEOUT:
                stale.append(serial)
                continue
            await send_json(writer, {"type": "ping"})

        for serial in stale:
            log.warning("Device timeout, closing: %s", serial)
            writer = device_connections.pop(serial, None)
            device_last_pong.pop(serial, None)
            if writer:
                writer.close()


# --- Main ---

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    log.info("TCP server listening on %s:%d", HOST, PORT)

    ping_task = asyncio.create_task(ping_loop())

    try:
        async with server:
            await server.serve_forever()
    finally:
        ping_task.cancel()


if __name__ == "__main__":
    print(f"Starting TCP server on {HOST}:{PORT}")
    print("Use netcat to test: nc localhost 9000")
    asyncio.run(main())
