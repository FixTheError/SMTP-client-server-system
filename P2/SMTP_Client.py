import socket
import sys
import re
import codecs
import Client_classes
if (len(sys.argv) == 3):
    sender_config = open(sys.argv[1], "r")
    receiver_config = open(sys.argv[2], "r")
    tmp = sender_config.readline()
    tmp_list = tmp.split("=")
    HOST = tmp_list[1]
    tmp = sender_config.readline()
    tmp_list = tmp.split("=")
    SMTP_Port = tmp_list[1]
    dumb = receiver_config.readline()
    tmp = receiver_config.readline()
    tmp_list = tmp.split("=")
    HTTP_Port = tmp_list[1]
else:
    print("Error, expected: SMTP_Client sender.conf reciever.conf")
ip_regex = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', HOST)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    done = False
    while(done != True):
        print ("For sender SMTP connection type SMTP, for reciever HTTP connection type HTTP\n")
        conn_type = input()
        if(conn_type == "SMTP"):
            s.connect((ip_regex[0], int(SMTP_Port)))
            Client_classes.SMTP_Handler(s)
            done = True
        elif(conn_type == "HTTP"):
            s.connect((ip_regex[0], int(HTTP_Port)))
            Client_classes.HTTP_Handler(s)
            done = True
        else:
            print("input not recognized.\n")
    