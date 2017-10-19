from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import chat_socket

import sys
import threading
import time
import re

# ウィンドウサイズの変更を許可するかのフラグ
NO_CHANGEING_WINDOW_SIZE = True

host = "*.*.*.*" # host name or IP
port = **** # port

# GUI Window Option
WINDOW_TITLE = "My Chat Server"
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 380

FONT_SIZE = 12

MODE_REGISTRATION = 10000
MODE_MAIN              = 11000

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		
		self.init()
		
	def init(self):
		
		self.setWindowTitle(WINDOW_TITLE)
		self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
		if NO_CHANGEING_WINDOW_SIZE:
			self.setMinimumHeight(WINDOW_HEIGHT)
			self.setMaximumHeight(WINDOW_HEIGHT)
			self.setMinimumWidth(WINDOW_WIDTH)
			self.setMinimumWidth(WINDOW_WIDTH)
			
		self.user_name = QTextEdit(self)
		self.user_name.move(WINDOW_WIDTH / 2 - 10 - 120, WINDOW_HEIGHT / 2  - 15)
		self.user_name.resize(120, 30)
		self.user_name.setFontPointSize(FONT_SIZE)
		
		self.user_label = QLabel("user name:", self)
		self.user_label.move(WINDOW_WIDTH / 2 -10 - 120 - 60, WINDOW_HEIGHT / 2 - 10)
		
		self.user_reg_btn = QPushButton("Connect",self)
		self.user_reg_btn.move(WINDOW_WIDTH  / 2 + 10, WINDOW_HEIGHT / 2 - 15)
		self.user_reg_btn.resize(60, 30)
		self.user_reg_btn.clicked.connect(self.connect_server)
		
		self.reg_label = QLabel("", self)
		self.reg_label.move(WINDOW_WIDTH / 2 - 10 - 120, WINDOW_HEIGHT / 2  + 15 + 10)
		self.reg_label.resize(200, 30)
		
		self.main_timeline_label = QLabel("Timeline", self)
		self.main_timeline = QTextEdit(self)
		
		self.main_timeline_label.move(10, 0)
		self.main_timeline.move(10, 20)
		
		self.main_timeline.resize(WINDOW_WIDTH - 20, 280)
		self.main_timeline.setFontPointSize(FONT_SIZE)
		self.main_timeline.setReadOnly(True)
		
		self.comment_edit = QTextEdit(self)
		self.comment_edit.move(10, 320)
		self.comment_edit.resize(WINDOW_WIDTH - 100 - 10, 50)
		self.comment_edit.setFontPointSize(FONT_SIZE)
		
		self.comment_label = QLabel("text", self)
		self.comment_label.move(10, 300)
		
		self.reg_btn = QPushButton("comment", self)
		self.reg_btn.move(WINDOW_WIDTH - 90, 340)
		self.reg_btn.resize(80, 30)
		self.reg_btn.clicked.connect(self.commenting)
		
		self.main_timeline.setVisible(False)
		self.main_timeline_label.setVisible(False)
		self.comment_edit.setVisible(False)
		self.comment_label.setVisible(False)
		self.reg_btn.setVisible(False)
		
		self.ctrl_enter = QShortcut(QKeySequence("Ctrl+Return"), self)
		self.ctrl_enter.activated.connect(self.ctrl_enter_bind)
		
		self.mode = MODE_REGISTRATION
		
		self.show()
			
	def connect_server(self):
		self.my_name = self.user_name.toPlainText().split('\n')[0]
		
		if len(self.my_name) < 1:
			self.reg_label.setText("ユーザー名が指定されていません")
			return
		
		self.mode = MODE_MAIN
		self.user_name.setVisible(False)
		self.user_reg_btn.setVisible(False)
		
		self.main_timeline.setVisible(True)
		self.main_timeline_label.setVisible(True)
		self.comment_edit.setVisible(True)
		self.comment_label.setVisible(True)
		self.reg_btn.setVisible(True)
		
		connect_thread = threading.Thread(target = self.setupConnection)
		connect_thread.setDaemon(True)
		
		connect_thread.start()
		
	
	def setupConnection(self):
		self.client = chat_socket.client(host, port)
		try_sec = 5
		while not self.client.connect():
			if try_sec > 60:
				self.main_timeline.append("[System] Maybe, server disabled")
				self.client = None
				return
				
			self.main_timeline.append("[System] Connection Faild, Retry after %d sec" % try_sec)
				
			time.sleep(try_sec)
			try_sec += try_sec / 2
			
		self.uniq_id = chat_socket.make_uniq_id()
		self.main_timeline.append("[System] Connected unique ID: " + self.uniq_id + "\n")
		
		# ユーザー判別ユニークIDとユーザー名をサーバーへ送って登録する
		self.client.send("*!new_set:%s:%s" % (self.my_name, self.uniq_id))
		
		self.update_thread = threading.Thread(target=self.update_timeline)
		self.update_thread.setDaemon(True)
		self.update_thread.start()
			
	def update_timeline(self):
		alive = True
		while alive and self.client:
			
			resa = self.client.recv()
			if resa:
				for res in resa.split('\0'):
					if not res:
						continue
					# サーバーからの特殊コマンド
					if re.match("\*\!", res):
					
						# サーバー切断要求
						if re.match("\*\!disconnect", res):
							alive = False
							break
					
					else:
						print(res)
						self.main_timeline.append(res)
						
			elif resa == None:
				pass
					
			elif resa == False:
				break
		
		self.main_timeline.append("Disconnected from server")
		self.client.close()
		self.client = None
		
	def commenting(self):
		text = self.comment_edit.toPlainText()
		
		if not self.client:
			return
		
		# 特殊コマンドをエスケープ
		if re.match("\*\!", text):
			return
		
		if len(text) > 0:
			self.client.send(text)
			
		self.comment_edit.clear()

	def ctrl_enter_bind(self):
		if self.mode == MODE_REGISTRATION:
			self.connect_server()
			
		elif self.mode == MODE_MAIN:
			self.commenting()

def main():
	app = QApplication(sys.argv)
	hWnd = MainWindow()
	sys.exit(app.exec_())
	
if __name__ == "__main__":
	main()
