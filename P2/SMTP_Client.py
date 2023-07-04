import socket
import sys
import re
import codecs
import Client_classes

#Check for the config files.
if (len(sys.argv) == 3):
    #Open the config files and read them into memory, assigning server information to variables..
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
    #Config files were not included, this should probably return.
    print("Error, expected: SMTP_Client sender.conf reciever.conf")

#Parse the host IP
ip_regex = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', HOST)

#Set up a TCP socket.
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    done = False
    
    while(done != True):
        #Get user input on what they're trying to do.
        print ("For sender SMTP connection type SMTP, for reciever HTTP connection type HTTP\n")
        conn_type = input()
        if(conn_type == "SMTP"):
            #User wants to send emails, connect and call SMTP handler.
            s.connect((ip_regex[0], int(SMTP_Port)))
            Client_classes.SMTP_Handler(s)
            done = True
        elif(conn_type == "HTTP"):
            #User wants to download emails, connect and call the HTTP handler.
            s.connect((ip_regex[0], int(HTTP_Port)))
            Client_classes.HTTP_Handler(s)
            done = True
        else:
            #Input not recognized, let the user know and prompt for input again.
            print("input not recognized.\n")
    
