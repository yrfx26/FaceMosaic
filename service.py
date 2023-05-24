# Echo server program
import os.path
import socket
import struct
import threading
from datetime import datetime

import torch

from detect_face import load_model, detect_one

weights = 'weight/yolo-face.pt'
device = torch.device('cpu')
model = load_model(weights, device)


HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 50020              # Arbitrary non-privileged port
MAX_LISTEN = 5
# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket:
#     socket.bind((HOST, PORT))
#     socket.listen(10)
#     conn, addr = socket.accept()
#     with conn:
#         print('Connected by', addr)
#         while True:
#             data = conn.recv(1024)
#             # if not data:
#             #     break
#             conn.sendall(data)


def log(addr, msg):
    print("{0} {1} {2}".format(datetime.now(), addr, msg))


def upload_image(socket, filepath, addr):
    fhead = struct.pack(b'128sq', bytes(os.path.basename(filepath), encoding='utf-8'),
                        os.stat(filepath).st_size)
    socket.send(fhead)
    fp = open(filepath, 'rb')
    while True:
        date = fp.read(1024)
        if not date:
            fp.close()
            break
        socket.send(date)


def deal_image(conn, addr):
    while True:
        fileinfo_size = struct.calcsize('128sq')
        buf = conn.recv(fileinfo_size)
        if buf:
            filename, filesize = struct.unpack('128sq', buf)
            fn = filename.decode().strip('\x00')
            filename = os.path.join(fn)
            recvd_size = 0
            fp = open(filename, 'wb')
            while not recvd_size == filesize:
                if filesize - recvd_size > 1024:
                    data = conn.recv(1024)
                    recvd_size += len(data)
                else:
                    data = conn.recv(1024)
                    recvd_size = filesize
                fp.write(data)  # 写入图片数据
            fp.close()
            log(addr, "图片接收完毕--" + fn)

            # TODO: 识别图片，
            new_filename = "detect_" + filename
            detect_one(model=model, image_path=filename, output_path=new_filename, device=device)
            log(addr, "图片打码完成--" + fn)
            # TODO：上传图片
            upload_image(conn, new_filename, addr)
            log(addr, "图片发送完毕--"+new_filename)


        else:
            log(addr, "远程主机断开")
            break


class Service(object):
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((HOST, PORT))
        self.socket.listen(MAX_LISTEN)

    def tcp_link(self, conn, addr):
        with conn:
            log(addr, "远程主机连接")
            deal_image(conn, addr)
            # except socket.error as msg:
            #     log(addr, msg)

    def close(self):
        cmd = input("")
        if cmd == "q":
            self.socket.close()
            exit(0)

    def start(self):
        close = threading.Thread(target=self.close)
        close.start()
        while True:
            conn, addr = self.socket.accept()
            tcp = threading.Thread(target=self.tcp_link, args=(conn, addr))
            tcp.start()


if __name__ == '__main__':
    service = Service()
    service.start()
