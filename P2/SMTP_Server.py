
import socket
import sys
import Server_classes
import threading



if (len(sys.argv) < 2):
    print ("config file not included")

SMTP_Thread = threading.Thread(target = Server_classes.SMTP_Handler, args = (sys.argv[1],))
HTTP_Thread = threading.Thread(target = Server_classes.HTTP_Handler, args = (sys.argv[1],))
SMTP_Thread.start()
HTTP_Thread.start()


            