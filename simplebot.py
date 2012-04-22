# sources
#
# IRC connection: http://oreilly.com/pub/h/1968
# multithreading: http://www.ibm.com/developerworks/aix/library/au-threadingpython/
# select: http://docs.python.org/library/select.html 
#         and "Programming Python" (Mark Lutz, 2006 3rd ed.) p.748f 

import threading
import datetime
import sys
import socket
import select
import string
import time

# configuration
HOST     = "irc.freenode.net"
PORT     = 6667
NICK     = "NICKNAMEAway"
IDENT    = "NICKNAMEAway"
REALNAME = "NICKNAMEAway"
CHANNEL  = "#testchan123"
LOG      = "log"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".log"
TIMEOUT  = 1 # in seconds

# for sharing data between user-input and server communication thread
mutex = threading.Lock()
command = ""


class IRCCommunicator(threading.Thread):
	def log(self, message):
		logoutput = open(LOG, 'a', 0)
		logline = datetime.datetime.now().strftime("%d.%m.%Y %H:%M > ") + repr(message)
		logoutput.write(logline + "\n")
		logoutput.close()

	def run(self):
		global command
		ircsocket=socket.socket( )
		ircsocket.connect((HOST, PORT))
		ircsocket.send("NICK %s\r\n" % NICK)
		ircsocket.send("USER %s %s bla :%s\r\n" % (IDENT, HOST, REALNAME))
		readbuffer=""

		now = datetime.datetime.now()
		print "%s running now: %s\n" % (self.getName(), now)

		shouldRun = True

		while shouldRun:
		  # check for input from the server
			readables, writeables, errors = select.select([ircsocket], [], [], TIMEOUT)
			if len(readables) == 0:
				# no input from server - check user input
				commandToSend = ""
				mutex.acquire()
				try: 
					if len(command) > 0:
						commandToSend = command
						command = ""
				finally:
					mutex.release() # early release of the lock to prevent stalling
				if len(commandToSend ) > 0:
					print("sending: " + commandToSend )
					self.log(commandToSend)
					ircsocket.send(commandToSend) # blocking send
					if commandToSend.find("QUIT") == 0:
						shouldRun = False
				# wait a bit for not run too fast
				time.sleep(1)
			else:
				for sockobj in readables:
					if sockobj == ircsocket:
						readbuffer=readbuffer+sockobj.recv(1024)
						temp=string.split(readbuffer, "\n")
						readbuffer=temp.pop( )

						for line in temp:
							line=string.rstrip(line)
							print(line)
							self.log(line)
							finegrainedline=string.split(line)

							# respond to ping to not get a timeout
							if(finegrainedline[0]=="PING"):
								ircsocket.send("PONG %s\r\n" % finegrainedline[1])
					else:
						print ("sockobj is not ircsocket")
						time.sleep(1)


irc = IRCCommunicator()
irc.setDaemon(True)
irc.start()

while(True):
	foundBotCommand = False
	data = sys.stdin.readline()
	if data.find("quit") == 0:
		print("goodbye")
		mutex.acquire()
		command = "QUIT goodbye\r\n"
		mutex.release()
		break
	if data.find("join") == 0:
		print("joining " + CHANNEL)
		mutex.acquire()
		command = "JOIN " + CHANNEL + "\r\n"
		mutex.release()
		foundBotCommand = True
	if data.find("part") == 0:
		print("leaving " + CHANNEL)
		mutex.acquire()
		command = "PART " + CHANNEL + "\r\n"
		mutex.release()
		foundBotCommand = True
	if data.find("help") == 0:
		print("commands for irc have to be prefixed by /")
		print("commands for this bot are help, join and quit")
		foundBotCommand = True
	if data.find("/") == 0:
		mutex.acquire()
		command = data[1:]
		mutex.release()
		foundBotCommand = True

	if not foundBotCommand:
		mutex.acquire()
		command = "PRIVMSG %s :%s\r\n" % (CHANNEL,data)
		mutex.release()

print ("waiting for irc-thread to finish")
irc.join()
