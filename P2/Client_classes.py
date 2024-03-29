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
                #Server terminated the connection, either in response to the QUIT command, or due to an error.
                print(msg)
                quit = True
            elif(msg_list[0] == "334"):
                #Server prompted user for username or password, get user input, encode, and send it.
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
                #Server sent a password for the new user and has now terminated the connection.
                #Decode and print the message, then close the socket and quit so the user can log in.
                tmp_64 = codecs.encode(msg_list[1], "utf-8")
                tmp = base64.b64decode(tmp_64)
                print_buf = "330 " + codecs.decode(tmp, "utf-8")
                print(print_buf)
                s.close()
                quit = True
            else:
                #Server responded with a code that doesn't require any further action, such as 250 OK
                print(msg)

#HTTP interface.
class HTTP_Handler:

    def __init__(self, s):
        #Set up flags for when to skip input and when to quit.
        #Emails are sent in packets that could be smaller than the entire email, so input isn't always needed. 
        done = False
        skip = False
        print("Type AUTH and hit enter to log in")
        while(done == False):
            #Get user input if needed, otherwise set skip back to false just in case.
            if(skip == False):
                cmd = input()
                b_cmd = codecs.encode(cmd, "utf-8")
                s.sendall(b_cmd)
            else:
                skip = False

            #recieve and parse the next server response.
            msg = s.recv(1024)
            message = codecs.decode(msg, "utf-8")
            
            
            msg_list = message.split()
            if(msg_list[0] == "535"):
                #Authentication faild and the server disconnected, close the socket and quit.
                print(message)
                s.close()
                return
            elif(msg_list[0] == "235"):
                #Authentication succeeded, print the message.
                print(message)
                #done = True
            elif(msg_list[0] == "330"):
                #Server responded with password for new user and terminated the connection.
                #print the message, close the socket, and return.
                tmp_64 = codecs.encode(msg_list[1], "utf-8")
                tmp = base64.b64decode(tmp_64)
                print_buf = "330 " + codecs.decode(tmp)
                print(print_buf)
                s.close()
                return
            elif(msg_list[0] == "334"):
                #Server has prompted the user for a username or password, decode and display the message.
                #Then set skip to true because the next command will either require user input to be encoded in base64, or not require input.
                tmp_64 = codecs.encode(msg_list[1], "utf-8")
                tmp = base64.b64decode(tmp_64)
                print_buf = "334 " + codecs.decode(tmp)
                print(print_buf)
                cmd = input()
                b_cmd = codecs.encode(cmd, "utf-8")
                cmd_64 = base64.b64encode(b_cmd)
                s.sendall(cmd_64)
                skip = True

        #Set up an answer variable to verify the command with the user and find or make a directoey to sytore emails/
        ans = 'n'
        if not os.path.exists("emails"):
            os.makedirs("emails")
        else:
            print("directory exists\n")

        #Get the username and number of emails the user wants to download and construct a command out of this information.
        while(ans =='n'):
            print("Enter your username.\n")
            usr = input()
            print("Enter the number of emails you would like to download.\n If this number is greater than the amount of emails you have, the server will only send as many as available.\n")
            count = int(input())
            get = "GET db/" + usr + "/ HTTP/1.1\nHost: 447.edu\nCount: " + str(count)
            print(get)
            #Verify the command with the user.
            print("\nIs this correct? y/n\n")
            ans = input()

        #Send the GET requwst and recieveand print the OK response.
        #Probably should have a conditional to make sure the response was an OK.
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
        #Recieve packets until the server finishes and write the data to an email file, and close the file when done.
        #It would make more sense to set up a loop to count the number of "./n" responses so each email can have its own file.
        #The connection should also be closed and the done flag set to done to terminate the transaction.
        while(msg != "250 OK"):
            message = s.recv(1024)
            msg = codecs.decode(message, "utf-8")
            print(msg)
            fp.write(msg)
        fp.close()
