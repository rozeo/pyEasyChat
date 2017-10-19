# coding: utf-8
#!/bin/python3.6

import socket
import collections
import threading
import time
import random

CONNECTION_ERRORS = (ConnectionRefusedError, ConnectionAbortedError, ConnectionResetError)
SECRET_CERT_KEY = "340523987510398123704"

def make_uniq_id(id_len = 12):
	sig = list("abcdefghijklmnopqrstuvwxyz0123456789")
	uid = []
	
	for i in range(0, id_len):
		uid.append(sig[random.randint(0, len(sig) - 1)])
	
	return "".join(map(str, uid))

class client():
	
	def __init__(self, host, port):
		self.host, self.port = host, port
		
		self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.client.settimeout(30)
		self.res = ""
	
	def connect(self):
		while True:
			try:
				self.client.connect((self.host, self.port))
				self.connection_flg = True
				return True
			
			except CONNECTION_ERRORS:
				return False
			
			except socket.timeout:
				return False
		
	def send(self, _str):
		if not self.connection_flg:
			return False
			
		while True:
			try:
				self.client.send(_str.encode('utf-8'))
				break
			
			except  CONNECTION_ERRORS:
				return False
			
			except socket.timeout:
				return False
			
		return True
	
	
	def recv(self, buffer_size = 4096):
		r = "".encode('utf-8')
		while True:
			try:
				res = self.client.recv(buffer_size)
				r += res
				if len(res) < buffer_size:
					break
			
			except CONNECTION_ERRORS:
				return False
			
			except socket.timeout:
				return False
		
		r = r.decode('utf-8')
		
		# keep-alive
		if len(r) <= 1:
			return None
		
		else:
			return r

	def close(self):
		self.client.close()
		self.connection_flg = False
