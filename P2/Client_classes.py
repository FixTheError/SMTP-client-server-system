import socket
import sys
import re
import codecs
import os
import select
import base64

#Handle SMTP connection
class SMTP_Handler:

    def __init__(self, s):
        #Create quit and skip flags for when the user quits and commands that don't need sequential input
        quit = False
        skip = False
        while (quit != True):
            #Get and send user input if necessary.
            if(skip == False):
                cmd = input()
                b_cmd = codecs.encode(cmd, "utf-8")
                s.sendall(b_cmd)
            else:
                #Set skip to false in case the next reply requires subsequent input
                skip = False

            #Receive and parse the next reply.
            b_msg = s.recv(1024)
            msg = codecs.decode(b_msg, "utf-8")
            msg_list = msg.split()
            if(msg_list[0] == "354"):
                #Sertver prompted user to start mail input
                print(msg)
                poll_obj = select.poll()
                poll_obj.register(s, select.POLLIN)
                done = False
                #Loop until the user is finished with their email.
                while(done == False):
                    #Poll will return an empty list if there is no reply.
                    #TThe server will only reply after encountering a line with just ".\n"
                    event_list = poll_obj.poll(1000)
                    for sock, event in event_list:
                        b_msg = s.recv(1024)
                        msg = codecs.decode(b_msg, "utf-8")
                        print(msg)
                        done = True
                        break
                    #User pressed enter, append a newline and send.
                    cmd = input() + "\n"
                    b_cmd = codecs.encode(cmd, "utf-8")
                    s.sendall(b_cmd)
                
            elif((msg_list[0] == "221") or (msg_list[0] == "535")):
                print(msg)
                quit = True
            elif(msg_list[0] == "334"):
                tmp_64 = codecs.encode(msg_list[1], "utf-8")
                tmp = base64.b64decode(tmp_64)
                print_buf = "334 " + codecs.decode(tmp)
                print(print_buf)
                cmd = input()
                b_cmd = codecs.encode(cmd, "utf-8")
                cmd_64 = base64.b64encode(b_cmd)
                s.sendall(cmd_64)
                skip = True
            elif(msg_list[0] == "330"):
                tmp_64 = codecs.encode(msg_list[1], "utf-8")
                tmp = base64.b64decode(tmp_64)
                print_buf = "330 " + codecs.decode(tmp, "utf-8")
                print(print_buf)
                s.close()
                quit = True
            else:
                print(msg)

class HTTP_Handler:

    def __init__(self, s):
        done = False
        skip = False
        print("Type AUTH and hit enter to log in")
        while(done == False):
            
            if(skip == False):
                cmd = input()
                b_cmd = codecs.encode(cmd, "utf-8")
                s.sendall(b_cmd)
            else:
                skip = False
            msg = s.recv(1024)
            message = codecs.decode(msg, "utf-8")
            
            
            msg_list = message.split()
            if(msg_list[0] == "535"):
                print(message)
                s.close()
                return
            elif(msg_list[0] == "235"):
                print(message)
                done = True
            elif(msg_list[0] == "330"):
                tmp_64 = codecs.encode(msg_list[1], "utf-8")
                tmp = base64.b64decode(tmp_64)
                print_buf = "330 " + codecs.decode(tmp)
                print(print_buf)
                s.close()
                return
            elif(msg_list[0] == "334"):
                
                tmp_64 = codecs.encode(msg_list[1], "utf-8")
                tmp = base64.b64decode(tmp_64)
                print_buf = "334 " + codecs.decode(tmp)
                print(print_buf)
                cmd = input()
                b_cmd = codecs.encode(cmd, "utf-8")
                cmd_64 = base64.b64encode(b_cmd)
                s.sendall(cmd_64)
                skip = True
                
        ans = 'n'

        if not os.path.exists("emails"):
            os.makedirs("emails")
        else:
            print("directory exists\n")
        while(ans =='n'):
            print("Enter your username.\n")
            usr = input()
            print("Enter the number of emails you would like to download.\n If this number is greater than the amount of emails you have, the server will only send as many as available.\n")
            count = int(input())
            get = "GET db/" + usr + "/ HTTP/1.1\nHost: 447.edu\nCount: " + str(count)
            print(get)
            print("\nIs this correct? y/n\n")
            ans = input()
        b_buf = codecs.encode(get, "utf-8")
        s.sendall(b_buf)
        message = s.recv(1024)
        msg = codecs.decode(message, "utf-8")
        print(msg)
        path = "emails"
        num_files = len([file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))])
        num_files += 1
        t_path = "emails/" + str(num_files)
        fp = open(t_path, "w")
        while(msg != "250 OK"):
            message = s.recv(1024)
            msg = codecs.decode(message, "utf-8")
            print(msg)
            fp.write(msg)
        fp.close()
