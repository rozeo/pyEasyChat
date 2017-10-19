#!/bin/python3.6
# coding: utf-8

import socket
import threading
import collections
import time
from datetime import datetime
import re

import chat_socket

IP = "*.*.*.*" # host name or IP
port = **** # port

# sending keep-alive interval
KEEP_ALIVE_INTERVAL = 20

DISCONNECT_REQUEST = "*!disconnect"

# make time string , format "%Y/%M/%d %H/%m/%s"
def make_timestr():
	nt = datetime.fromtimestamp(time.time())
	
	return ("%04d/%02d/%02d %02d:%02d:%02d" % (nt.year, nt.month, nt.day, nt.hour, nt.minute, nt.second))

# user infomation
class client_info():
	def __init__(self, client, host):
		self.client = client
		self.host   = host
		self.uniq_id = None
		self.name = None
		
		self.disconnect_require = False
		
		self.client.setblocking(False)
		
	def setUserInfo(self, name,id_str):
		self.uniq_id = id_str
		self.name = name
		
	# recv, send, closeを簡単にオーバーライドしてbyte文字列からstr文字列に変換する
		
	def recv(self, buffer_size = 4096):
		return self.client.recv(buffer_size)
	
	def send(self, _str):
		self.client.send(_str.encode("utf-8"))
		
	def requiest_disconnect(self):
		self.disconnect_require = True
		
	def close(self):
		self.client.close()

class server_main():
	def __init__(self, host, port, max_listen = 10):
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setblocking(False)
		self.server.bind((host, port))
		self.server.listen(max_listen)
		self.max_listen = max_listen
		
		# クライアントのソケットのリスト
		self.clientList = [None for i in range(max_listen)]
		self.connections = 0
		self.recv_queue = collections.deque()
		
		# 新しい接続を受け付けるスレッド
		self.new_client_thread = threading.Thread(target = self.NewClient)
		self.new_client_thread.setDaemon(True)
		
		# 送られてくるパケットをチェックする
		self.incoming_thread = threading.Thread(target = self.check_incoming)
		self.incoming_thread.setDaemon(True)
		
		# 送られてきたパケットを接続されているクライアントへ送る
		self.send_thread = threading.Thread(target = self.sending)
		self.send_thread.setDaemon(True)
		
		self.server_kill = threading.Event()
		
		self.new_client_thread.start()
		self.incoming_thread.start()
		self.send_thread.start()

	# 新しい接続を受け付ける
	def NewClient(self):
		while not self.server_kill.is_set():
			try:
				client, info = self.server.accept()
			
			except BlockingIOError:
				continue
			
			c_flg = False
			cid = -1
			for i in range(0, self.max_listen):
				if self.clientList[i] == None:
					self.clientList[i] = client_info(client, info[0])
					cid = i
					c_flg = True
					break
				
			if c_flg:
				print("NEW CONNECTION from %s id:%d" % (info[0], cid))
				self.connections += 1
			
			else:
				print("CONNECTION DENY from %s" % (info[0]))
				
	def check_incoming(self):
		
		keep_alive = time.time()
		rkeep_alive = keep_alive
		
		while not self.server_kill.is_set():
			
			for i in range(0, self.max_listen):
				if self.clientList[i] == None:
					continue
				
				if self.clientList[i].disconnect_require:
					self.closeClient(i)
					continue
				
				r = ""
				while True:
					try:
						k = self.clientList[i].recv()
						r += k.decode("utf-8")
						if len(k) < 4096:
							break
					
					# recvできるパケットが来ていない
					except BlockingIOError:
						break
					
					# ソケットに接続できないエラー
					except chat_socket.CONNECTION_ERRORS:
						self.closeClient(i)
						r = False
						break
				
				if r:
					# 新しく参加ユーザー情報を登録する
					if re.match("\*\!new_set", r):
						d, name, uniq_id = r.split(":")
						self.clientList[i].setUserInfo(name, uniq_id)
						print("[%s] NEW USER DEFINED [id: %d, name: %s, uniq_id: %s]" % (make_timestr(), i, name, uniq_id))
						
						# 現在参加しているユーザーのリストを生成
						user_list = ""
						for j in range(0, self.max_listen):
							if self.clientList[j] and self.clientList[i].name and self.clientList[i].uniq_id:
								user_list += self.clientList[j].name + " [uniq_id: " + self.clientList[j].uniq_id + "]\n"
						
						self.recv_queue.append([i + self.max_listen, "Now Connecting Users: " + str(self.connections) + "\nUser List:\n" + user_list])
						
						# 新しい参加者を通知する
						self.recv_queue.append([-1, "USER %s [uniq_id: %s] joined" % (name, uniq_id)])
						
					else:
						# ユーザー名とユニークIDがセットされていないユーザーは切断する
						if not self.clientList[i].name or not self.clientList[i].uniq_id:
							self.userClose(i)
							break
						
						self.recv_queue.append([i, r])
						print("[%s] %s(id:%s): %s" % (make_timestr(), self.clientList[i].name, self.clientList[i].uniq_id, r))
						
			# keep-aliveを生成
			keep_alive = time.time()
			if keep_alive > rkeep_alive:
				if keep_alive - rkeep_alive > KEEP_ALIVE_INTERVAL:
					self.recv_queue.append([-1, ""])
					rkeep_alive = keep_alive
					
	def sending(self):
		while True:
			if len(self.recv_queue) > 0:
				response = self.recv_queue.popleft()
				
				# id指定がmax_listen以上の場合は1人に対しての送信として扱う
				if response[0] >= self.max_listen:
					while True:
							try:
								self.clientList[response[0] % self.max_listen].send(response[1] + '\0')
								break
						
							except chat_socket.CONNECTION_ERRORS:
								self.closeClient(response[0] % self.max_listen)
								break
							
							except BlockingIOError:
								continue
							
					if response[1] == DISCONNECT_REQUEST:
						self.clientList[response[0] % self.max_listen].requiest_disconnect()
					
				else:
					
					 # id が 0以下の場合はシステムメッセージとして扱う
					for i in range(0, self.max_listen):
						if self.clientList[i]:
							if not self.clientList[i].name or not self.clientList[i].uniq_id:
								continue
						
							if response[0] < 0:
								
								# サーバー側からクライアントに向けて送る特殊コマンド
								if re.match("\*\!", response[1]):
									send_str = response[1] + '\0'
								
								# keep-alive
								elif response[1] == "":
									send_str = "\0"
									
								# それ以外の場合は通常どおり送信
								else:
									send_str = ("[%s] Server : %s" % (make_timestr(), response[1])) + '\0'
					
							else:
								send_str = "[%s] %s(id:%s) : %s" % (make_timestr(),
																			     self.clientList[response[0]].name,
																		         self.clientList[response[0]].uniq_id,
																				 response[1]) + '\0'
							
							while True:
								try:
									self.clientList[i].send(send_str)
									break
							
								except chat_socket.CONNECTION_ERRORS:
									self.closeClient(i)
									break
								
								except (BlockingIOError):
									continue
			
			else:
				if self.server_kill.is_set():
					break
	
	def closeClient(self, cid):
		self.clientList[cid].close()
		print("DISCONNECTED %s id:%d" % (self.clientList[cid].host, cid))
		name = self.clientList[cid].name
		uid = self.clientList[cid].uniq_id
		self.clientList[cid] = None
		
		self.recv_queue.append([cid, "[%s] USER %s [uniq_id: %s] leaved" % (make_timestr(), name, uid)])
		self.connections -= 1
		
	def userClose(self, cid):
		self.recv_queue.append([cid + self.max_listen, DISCONNECT_REQUEST])
				
	def kill(self):
		# 接続中のクラインアントに接続断を通知
		self.recv_queue.append([-1, DISCONNECT_REQUEST])
				
		self.server_kill.set()
		self.new_client_thread.join()
		self.incoming_thread.join()
		self.send_thread.join()
		
		for i in range(self.max_listen):
			if self.clientList[i]:
				self.closeClient(i)

def main():
	
	server = server_main(IP, port, 100)
	print("[%s] Starting Chat Server" % make_timestr())
	input()
	server.kill()
	print("[%s] Stoped Chat Server" % (make_timestr()))
	
if __name__ == "__main__":
	main()
	
