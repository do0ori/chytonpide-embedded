"""간단한 control client - 디바이스 상태 변경 테스트용.

사용:
  python set_device.py led on
  python set_device.py led off
  python set_device.py face HAPPY
  python set_device.py face SAD
  python set_device.py face NEUTRAL
"""
import socket, json, sys

SERIAL = "xJN2wsF850yqWQfBUkGP"
HOST = "localhost"
PORT = 9000

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd, val = sys.argv[1], sys.argv[2]
    msg = {"type": "set_device", "serial": SERIAL}

    if cmd == "led":
        msg["is_led_on"] = val.lower() in ("on", "true", "1")
    elif cmd == "face":
        msg["face"] = val.upper()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    s = socket.socket()
    s.connect((HOST, PORT))
    s.sendall((json.dumps(msg) + "\n").encode())
    s.settimeout(2)
    try:
        resp = s.recv(1024).decode().strip()
        print(f"Server: {resp}")
    except socket.timeout:
        print("No response")
    s.close()

if __name__ == "__main__":
    main()
