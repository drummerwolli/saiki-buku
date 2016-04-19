def run(ip, port=9092):
    import socket
    from time import sleep
    timeout_count = 0
    while timeout_count < 10:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((ip, port))
        if result == 0:
            return True
        else:
            timeout_count += 1
            sleep(10)
    return False
