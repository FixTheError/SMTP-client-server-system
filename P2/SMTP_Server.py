
import socket
import sys
import Server_classes
import threading


#Make sure the config file was included as a parameter.
if (len(sys.argv) < 2):
    print ("config file not included")

#Create and start threads for handling SMTP and HTTP clients.
SMTP_Thread = threading.Thread(target = Server_classes.SMTP_Handler, args = (sys.argv[1],))
HTTP_Thread = threading.Thread(target = Server_classes.HTTP_Handler, args = (sys.argv[1],))
SMTP_Thread.start()
HTTP_Thread.start()


            
