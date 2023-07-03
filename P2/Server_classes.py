import socket
import os
import codecs
from datetime import datetime
from pathlib import Path
import time
import threading
import re
import base64
import random
import string
#container for information about a connection
mutex = threading.Semaphore()
class user:
    #Initialize a new user
    def __init__(self, name, conn, addr):
        self.name = name
        self.alias = ""
        self.frm = ""
        self.conn = conn
        self.addr = addr
        self.rcpt = []
        self.data = ""
        self.ready = False
        self.quit = False
        self.registered = False
        self.serv = False

class remote_server:
    #Initialize a server
    def __init__(self, domain, ip, port):
        self.domain = domain
        self.ip = ip
        self.port = port
        self.ip_regex = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', self.ip)
        

remote_servs = []

class SMTP_Handler:
    
    #set up listener
    def __init__(self, conf):
        #Read in the configuration file and parse
        mutex.acquire()
        config = open(conf, "r")
        lines = config.readlines()
        config.close()
        mutex.release()
        self.local_domain = lines[0]
        self.local_domain = self.local_domain.strip()
        print(self.local_domain + "\n")
        tmp = lines[1]
        tmp_list = tmp.split("=")
        port = tmp_list[1]
        lnum = 3
        #initialize known servers
        while(lnum < len(lines)):
            remote_name = lines[lnum].strip()
            lnum += 1
            tmp = lines[lnum]
            tmp_list = tmp.split("=")
            remote_ip = tmp_list[1]
            lnum += 1
            tmp = lines[lnum]
            tmp_list = tmp.split("=")
            remote_port = tmp_list[1]
            lnum += 1
            external = remote_server(remote_name, remote_ip, remote_port)
            remote_servs.append(external)

        #Set up an array for threads and set up directory to act as a database
        threads = []
        mutex.acquire()
        if not os.path.exists('db'):
            os.makedirs('db')
        mutex.release()
        # Set up a listener and create a new thread for each connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            myhost = socket.gethostname()
            self.HOST = socket.gethostbyname(myhost)
            s.bind((self.HOST, int(port)))
            while(True):
                s.listen()
                conn, addr = s.accept()
                print ("got SMTP connection from ", addr)
                usr = user("", conn, addr)
                t = threading.Thread(target = self.Handle_Client, args = (usr,))
                threads.append(t)
                t.start()
        return

    #log server replies
    def log_reply(self, rep, usr):
        log_ent = str(datetime.now()) + " from: " + self.HOST + " To: " + usr.addr[0] + " " + rep + "\n"
        print(log_ent)
        mutex.acquire()
        lf = open(".server_log", "a")
        lf.write(log_ent)
        lf.close()
        mutex.release()
        return

    #log messages from users
    def log_incoming(self, rep, frm):
        log_ent = str(datetime.now()) 
        log_ent = log_ent + " from: " 
        log_ent = log_ent + frm 
        log_ent = log_ent + " To: " 
        log_ent = log_ent + self.HOST 
        log_ent = log_ent + " " 
        log_ent = log_ent + rep 
        log_ent = log_ent + "\n"
        print(log_ent)
        mutex.acquire()
        lf = open(".server_log", "a")
        lf.write(log_ent)
        lf.close()
        mutex.release()
        return

    #Handle client connections
    def Handle_Client(self, usr):
        #main loop, repeats until user sends a quit command
        while(usr.quit == False):
            #recieve and split the new message
            message = usr.conn.recv(1024)
            msg = codecs.decode(message, "utf-8")
            self.log_incoming(msg, usr.addr[0])
            msg_list = msg.split()
            #take appropriate action according to RFC command
            if(msg_list[0] == "HELO"):
                retrn = self.HELO(msg, usr)
                if(retrn == 0):
                    #There is an impostor among us, abort mission! Run for the hills!
                    usr.quit = True
                    usr.conn.close()
            elif(msg_list[0] == "AUTH"):
                self.AUTH(msg, usr)
            elif(msg_list[0] == "MAIL"):
                self.MAIL_FROM(msg, usr)
            elif(msg_list[0] == "RCPT"):
                self.RCPT_TO(msg, usr)
            elif(msg_list[0] == "DATA:"):
                self.DATA(msg, usr)
            elif(msg_list[0] == "HELP"):
                self.HELP(msg, usr)
            elif(msg_list[0] == "QUIT"):
                self.QUIT(msg, usr)
            else:
                rep = "500 Syntax error, command unrecognized\n"
                self.log_reply(rep, usr)
                usr.conn.sendall(b"500 Syntax error, command unrecognized\n")
        return
    
    #Handle HELO
    def HELO(self, msg, usr):
        msg_list = msg.split(" ")
        #Check for parameters
        if(len(msg_list) < 2):
            rep = "501 Syntax error in parameters or arguments: expected user\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"501 Syntax error in parameters or arguments: expected user\n")
            return

        #Remote servers will only pass 2 parameters, looks like "HELO example.ex wewillalwaysbepartofthegreatmisdirect"
        if(len(msg_list) == 3):
            #Check for secret phrase
            if(msg_list[2] == "wewillalwaysbepartofthegreatmisdirect"): #BTBAM rules!
                for serv in remote_servs:
                    if(serv.domain == msg_list[1]):
                        #send the OK code, log the reply, and register the domain as a special user connection
                        rep = "250 OK\n"
                        self.log_reply(rep, usr)
                        usr.conn.sendall(b"250 OK\n")
                        usr.name = serv.domain
                        usr.registered = True
                        usr.serv = True
                        return 1
                return 0
        #send welcome reply andregister the user connection
        rep = "250 " + self.local_domain + " Welcome to " + self.local_domain + " SMTP server\n"
        self.log_reply(rep, usr)
        b_rep = codecs.encode(rep, "utf-8")
        usr.conn.sendall(b_rep)
        msg_list[1].strip()
        usr.alias = msg_list[1]
        return 1

    #User authentication
    def AUTH(self, msg, usr):
        #Encode and send reply prompting for username
        code = b"334 "
        usr_tail = b"username"
        pass_tail = b"password"
        usr_tail = base64.b64encode(usr_tail)
        pass_tail = base64.b64encode(pass_tail)
        user_msg = code + usr_tail
        rep = codecs.decode(user_msg, "utf-8") + "\n"
        self.log_reply(rep, usr)
        usr.conn.sendall(user_msg)
        #receive username, decode, and load the hidden password file into memory
        name_64 = usr.conn.recv(1024)
        self.log_incoming(codecs.decode(name_64, "utf-8"), usr.addr[0])
        temp = base64.b64decode(name_64)
        name = codecs.decode(temp, "utf-8")
        name = name.strip()
        mutex.acquire()
        pth = Path("db/")
        pth = os.path.join(pth, ".user_pass")
        usr_pass = open(pth, "r+")
        lines = usr_pass.readlines()
        usr_pass.close()
        mutex.release()
        found = False
        pwrd = ""
        match = ""
        #Check the contents of the password file for a matching username
        for line in lines:
            tmp = line.split("=")
            if((len(tmp) == 2) and (tmp[0] == name)):
               match = tmp[1].strip()
               found = True
               break
        if (found):
            #This user exists on this server. Encode and send password prompt
            pass_msg = code + pass_tail
            rep = codecs.decode(pass_msg, "utf-8") + "\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(pass_msg)
            #Receive encoded password, log it, then decode it
            pass_64 = usr.conn.recv(1024)
            self.log_incoming(codecs.decode(pass_64, "utf-8"), usr.addr[0])
            temp = base64.b64decode(pass_64)
            #Salt the decoded password, re-encode, and compare to the stored password to check validity
            salt = b"447S21" + temp
            b_salt = base64.b64encode(salt)
            salt_64 = codecs.decode(b_salt, "utf-8")
            if(salt_64 == match):
                #The user is who they say they are. Log, encode, and send tthe success response, then name and register the connection
                rep = "235 2.7.0 Authentication Succeeded\n"
                self.log_reply(rep, usr)
                usr.conn.sendall(b"235 2.7.0 Authentication Succeeded\n")
                usr.name = name
                usr.registered = True
            else:
                #Invalid password, log, encode, and send failure response. Then close the connection and allow this thread to return
                rep = "535 2.7.0 Authentication credentials invalid, terminating\n"
                self.log_reply(rep, usr)
                usr.conn.sendall(b"535 2.7.0 Authentication credentials invalid, terminating\n")
                usr.quit = True
                usr.conn.close()
        else:
            #this is a new user, create a password for this user and store it
            #I probably did this in the most goofy way possible, but I think I was running low on time and overthinking
            chars = string.digits + string.ascii_letters
            r_string = "".join(random.choice(chars) for i in range(6))
            b_string = codecs.encode(r_string, "utf-8")
            salt = b"447S21" + b_string
            b_string = base64.b64encode(b_string)
            s_buf = b"330 " + b_string
            w_buf = codecs.encode(name, "utf-8") + b"=" + base64.b64encode(salt) + b"\n"
            wr_buf = codecs.decode(w_buf, "utf-8")
            mutex.acquire()
            usr_pass = open("db/.user_pass", "a")
            usr_pass.write(wr_buf)
            usr_pass.close()
            mutex.release()
            #log and send reply containing the password for the new user. 
            #Then terminate connection and set quit to true to allow this thread to return so the user can log in with their new password.
            rep = codecs.decode(s_buf, "utf-8") + "\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(s_buf)
            usr.quit = True
            usr.conn.close()
            #Create a new directory for this user's emails.
            path = "db/" + name
            mutex.acquire()
            if not os.path.exists(path):
                os.makedirs(path)
            mutex.release()
        return

    #Start a new email.
    def MAIL_FROM(self, msg, usr):
        #Make sure this user is authenticated, if not, log and send error reply to remind the user to use AUTH first.
        if (usr.registered == False):
            rep = "503 Bad sequence of commands: expected AUTH\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"503 Bad sequence of commands: expected AUTH\n")
            return
        msg_list = msg.split()
        #Syntax check, make sure the command includes an address parameter as the only parameter.
        if((msg_list[1] == "FROM:") and (len(msg_list) == 3)):
            #Syntax check, make sure address parameter includes a domain.
            if (msg_list[2].count('@') == 1):
                #Split the address parameter and check if the domain provided matches the local domain.
                tmp_list = msg_list[2].split("@")
                if((len(tmp_list) == 2) and (tmp_list[1] != self.local_domain)):
                    #Is this another server forwarding an email to a user on this domain?
                    if(usr.serv == False):
                        #This connection is not a remote server, log and send domain mismatch error response and return to main loop.
                        rep = "501 Syntax error in parameters or arguments: domain mismatch\n"
                        self.log_reply(rep, usr)
                        usr.conn.sendall(b"501 Syntax error in parameters or arguments: domain mismatch\n")
                        return
                    #This is another domain forwarding an email to a user in this one.
                    #Find the domain, log and send the OK reply, and set the from buffer for this connection.
                    for serv in remote_servs:
                        if(serv.domain == tmp_list[1]):
                            rep = "250 OK\n"
                            self.log_reply(rep, usr)
                            usr.conn.sendall(b"250 OK\n")
                            usr.frm = tmp_list[0]
                            return
                #Make sure the user didn't type user@ without a domain.
                #I think this could have just been elif ((len(tmp_list) == 2)), I was probably just overthinking.
                elif((len(tmp_list) == 2) and (tmp_list[1] == self.local_domain)):
                    #Check if the usernames match
                    if(usr.name == tmp_list[0]):
                        #Usernames match, log and send OK response, then set the from buffer.
                        rep = "250 OK\n"
                        self.log_reply(rep, usr)
                        usr.conn.sendall(b"250 OK\n")
                        usr.frm = msg_list[2]
                    else:
                        #User either typed their username incorrectly, or is up to sometthing malicious.
                        #log and send mailbox not allowed code.
                        rep = "553 Requested action not taken: mailbox name not allowed\n"
                        self.log_reply(rep, usr)
                        usr.conn.sendall(b"553 Requested action not taken: mailbox name not allowed\n")
                    return
            else:
                #User formatted their email address wrong, log and send syntax error code for address format.
                rep = "501 Syntax error in parameters or arguments: expected user@" + self.local_domain + "\n"
                self.log_reply(rep, usr)
                b_rep = codecs.encode(rep, "utf-8")
                usr.conn.sendall(b_rep)
        elif(msg_list[1] != "FROM:"):
            #User did not type out the full command name, log and send syntax error response.
            rep = "500 Syntax error, command unrecognized: expected MAIL FROM: user@" + self.local_domain + "\n"
            self.log_reply(rep, usr)
            b_rep = codecs.encode(rep, "utf-8")
            usr.conn.sendall(b_rep)
        elif(len(msg_list) > 3):
            #User included extra parameters, this server only supports the address parameter.
            #Log and send oarameters not recognized response for MAIL FROM:/RCPT TO commands.
            rep = "555 MAIL FROM/RCPT TO parameters not recognized or not implemented\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"555 MAIL FROM/RCPT TO parameters not recognized or not implemented\n")
        return

    #Specify a recipient.
    def RCPT_TO(self, msg, usr):
        #See if the command is recognized.
        msg_list = msg.split()
        if((msg_list[1] == "TO:") and (len(msg_list) == 3)):
            #Make sure the parameter contains a username and domain.
            if (msg_list[2].count('@') == 1):
                #Does the domain match?
                tmp_list = msg_list[2].split("@")
                if((len(tmp_list) == 2) and (tmp_list[1] == self.local_domain)):
                    #Domain matches, log and send OK reply. Then add the address to the user's recipient buffer.
                    rep = "250 OK\n"
                    self.log_reply(rep, usr)
                    usr.conn.sendall(b"250 OK\n")
                    usr.rcpt.append(msg_list[2])
                    #Make sure the recipient has a directory.
                    #There should be an extra if to make sure the user exists.
                    #No sense in creating zombie accounts.
                    path = "db/" + tmp_list[0]
                    mutex.acquire()
                    if not os.path.exists(path):
                        os.makedirs(path)
                    mutex.release()
                    usr.ready = True
                elif(len(tmp_list) == 2):
                    #Recipient is not on this domain, see if they're on a recognized.
                    f = False
                    for serv in remote_servs:
                        if(serv.domain == tmp_list[1]):
                            f = True
                            break
                    if f:
                        #Found the remote server.
                        #Log and send "will forward" reply, add the address to recipient buffer, and allow for DATA command.
                        rep = "251 User not local; will forward\n"
                        self.log_reply(rep, usr)
                        usr.conn.sendall(b"251 User not local; will forward\n")
                        usr.rcpt.append(msg_list[2])
                        usr.ready = True
                        
                    else:
                        #No match found. log and send domain not supported error.
                        rep = "450 Requested mail action not taken: domain not supported\n"
                        self.log_reply(rep, usr)
                        usr.conn.sendall(b"450 Requested mail action not taken: domain not supported\n")
                else:
                    rep = "501 Syntax error in parameters or arguments: domain mismatch\n"
                    self.log_reply(rep, usr)
                    usr.conn.sendall(b"501 Syntax error in parameters or arguments: domain mismatch\n")
            else:
                #Address syntax is wrong. Log and send syntax error reply.
                rep = "501 Syntax error in parameters or arguments: expected user@" + self.local_domain + "\n"
                self.log_reply(rep, usr)
                b_rep = codecs.encode(rep, "utf-8")
                usr.conn.sendall(b_rep)
        elif(msg_list[1] != "TO:"):
            #User forgot to include the TO: part. Log and send syntax error response.
            rep = "500 Syntax error, command unrecognized: expected RCPT TO: user@" + self.local_domain + "\n"
            self.log_reply(rep, usr)
            b_rep = codecs.encode(rep, "utf-8")
            usr.conn.sendall(b_rep)
            #usr.conn.sendall(b"500 Syntax error, command unrecognized: expected RCPT TO: user@447.edu\n")
        elif(len(msg_list) > 3):
            #User included too many parameters. Log and send parameters not recognized reply.
            rep = "555 MAIL FROM/RCPT TO parameters not recognized or not implemented\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"555 MAIL FROM/RCPT TO parameters not recognized or not implemented\n")
        return

    #Get the contents of the email.
    def DATA(self, msg, usr):
        msg_list = msg.split()
        if(len(msg_list) == 1):
            #No parameters needed, has the user completed the correct sequence of commands?
            if ((len(usr.rcpt) != 0) and usr.ready):
                #Ready to recieve data, let the user know and recieve the data, then put it in the buffer.
                rep = "354 Start mail input; end with <CRLF>.<CRLF>\n"
                self.log_reply(rep, usr)
                usr.conn.sendall(b"354 Start mail input; end with <CRLF>.<CRLF>\n")
                message = usr.conn.recv(1024)
                self.log_incoming(codecs.decode(message, "utf-8"), usr.addr[0])
                msg1 = codecs.decode(message, "utf-8")
                usr.data += msg1
                #Loop until the user terminates the email.
                while(msg1 != ".\n"):
                    message = usr.conn.recv(1024)
                    self.log_incoming(codecs.decode(message, "utf-8"), usr.addr[0])
                    msg1 = codecs.decode(message, "utf-8")
                    usr.data += msg1

                #Find all local recipients and add a file containing the email to their directories.
                for rcpt in usr.rcpt:
                    rcpt_lst = rcpt.split("@")
                    if(rcpt_lst[1] == self.local_domain):
                        print("domain")
                        path ="db/" + rcpt_lst[0]
                        num_files = len([file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))])
                        num_files += 1
                        fn = str(num_files) +".email"
                        path += "/" + fn
                        mutex.acquire()
                        fp = open(path, "w")
                        temp = "Date: " + str(datetime.now()) + "\n"
                        fp.write(temp)
                        temp = "From: " + usr.frm + "@" + self.local_domain + "\n"
                        fp.write(temp)
                        temp = "To: " + rcpt + "\n"
                        fp.write(temp)
                        fp.write(usr.data)
                        fp.close()
                        mutex.release()
                    else:
                        #Find the remote server the recipient is on
                        found = None
                        for serv in remote_servs:
                            if (serv.domain == rcpt_lst[1]):
                                found = serv
                                break

                        if found is not None:
                            #Create a new connection  to the remote server.
                            print("found")
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            ret = s.connect_ex((found.ip_regex[0], int(found.port)))
                            if (ret == 0):
                                #Create a user for this connection and forward the email by following a slightly altered sequence of commands.
                                tmp_usr =  user("", s, found.ip)#This is probably unnecessary.
                                msg = "HELO " + self.local_domain + " wewillalwaysbepartofthegreatmisdirect"
                                send_it = codecs.encode(msg, "utf-8")
                                self.log_reply(msg, tmp_usr)
                                s.sendall(send_it)
                                rep = s.recv(1024)
                                self.log_incoming(codecs.decode(rep, "utf-8"), usr.addr[0])
                                msg = "MAIL FROM: " + usr.frm + "\n"
                                send_it = codecs.encode(msg, "utf-8")
                                self.log_reply(msg, tmp_usr)
                                s.sendall(send_it)
                                rep = s.recv(1024)
                                self.log_incoming(codecs.decode(rep, "utf-8"), usr.addr[0])
                                msg = "RCPT TO: " + rcpt + "\n"
                                send_it = codecs.encode(msg, "utf-8")
                                self.log_reply(msg, tmp_usr)
                                s.sendall(send_it)
                                rep = s.recv(1024)
                                self.log_incoming(codecs.decode(rep, "utf-8"), usr.addr[0])
                                msg = "DATA:\n"
                                send_it = codecs.encode(msg, "utf-8")
                                self.log_reply(msg, tmp_usr)
                                s.sendall(send_it)
                                rep = s.recv(1024)
                                self.log_incoming(codecs.decode(rep, "utf-8"), usr.addr[0])
                                lines = usr.data.split("\n")
                                for line in lines:
                                    if(line == "."):
                                        line = ".\n"
                                    send_it = codecs.encode(line, "utf-8")
                                    self.log_reply(line, tmp_usr)
                                    s.sendall(send_it)
                                rep = s.recv(1024)
                                self.log_incoming(codecs.decode(rep, "utf-8"), usr.addr[0])
                                #Quit and close the connection.
                                msg = "QUIT\n"
                                send_it = codecs.encode(msg, "utf-8")
                                self.log_reply(msg, tmp_usr)
                                s.sendall(send_it)
                                rep = s.recv(1024)
                                self.log_incoming(codecs.decode(rep, "utf-8"), usr.addr[0])
                                s.close()
                            else:
                                #Could not connect to the remote server, log and send failure response.
                                rep = "554 Transaction failed: remote server offline\n"
                                self.log_reply(rep, usr)
                                usr.conn.sendall(b"554 Transaction failed: remote server offline\n")
                                return
                        else:
                            print("debug: domain not supported")

                #Clear buffers and send OK
                usr.rcpt.clear()
                usr.data = ""
                rep = "250 OK\n"
                self.log_reply(rep, usr)
                usr.conn.sendall(b"250 OK\n")
            else:
                #User forgot one or more of the previous commands, send notification.
                rep = "503 Bad sequence of commands: expected RCPT TO: user@domain.edu\n"
                self.log_reply(rep, usr)
                usr.conn.sendall(b"503 Bad sequence of commands: expected RCPT TO: user@domaim.edu\n")
        else:
            #User included unsupported parameters, send parameter error response.
            rep = "504 Command parameter not implemented\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"504 Command parameter not implemented\n")
            
        return

    ##Tell user how to use the server properly.
    def HELP(self, msg, usr):
        msg_list = msg.split(" ",1)
        #General help, send a list of commands and the proper sequence for them.
        if(len(msg_list) == 1):
            rep = "214 Available commands: HELO, AUTH, MAIL FROM:, RCPT TO:, DATA:, QUIT\nMail sequence: HELO, AUTH, MAIL FROM, RCPT TO, DATA\nUser must register with the HELO command first.\nFor help with specific commands type HELP command\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"214 Available commands: HELO, AUTH, MAIL FROM:, RCPT TO:, DATA:, QUIT\nMail sequence: HELO, AUTH, MAIL FROM, RCPT TO, DATA\nUser must register with the HELO command first.\nFor help with specific commands type HELP command\n")
        #Tell the user how to use HELO..
        elif(msg_list[1] == "HELO"):
            rep = "214 Syntax: HELO username\nThis command registers the user connection and must be called before attempting to make a mail transaction.\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"214 Syntax: HELO username\nThis command registers the user connection and must be called before attempting to make a mail transaction.\n")
        #Tell the user how to use AUTH.
        elif(msg_list[1] == "AUTH"):
            rep = "214 Syntax: AUTH\nThis command registers the user and must be called before attempting to make a mail transaction.\nYou will be prompted for login info, new users will recieve a password and disconnect once AUTH succeeds\nYou may then proceed to restart the connection\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"214 Syntax: AUTH\nThis command registers the user and must be called before attempting to make a mail transaction.\nYou will be prompted for login info, new users will recieve a password and disconnect once AUTH succeeds\nYou may then proceed to restart the connection\n")
        #Tell the user how to use MAIL FROM.
        elif((msg_list[1] == "MAIL FROM:") or (msg_list[1] == "MAIL")):
            rep = "214 Syntax: MAIL FROM: user\nMake sure to use the same name you used in the HELO command.\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"214 Syntax: MAIL FROM: user\nMake sure to use the same name you used in the HELO command.\n")
        #Tell the user how to specify recipients
        elif((msg_list[1] == "RCPT TO:") or (msg_list[1] == "RCPT")):
            rep = "214 Syntax: RCPT TO: user\nThere is no guarantee that user exists, but if not a new folder will be created.\nFor multiple users, multiple subsequent RCPT TO commands can be issued before DATA\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"214 Syntax: RCPT TO: user\nThere is no guarantee that user exists, but if not a new folder will be created.\nFor multiple users, multiple subsequent RCPT TO commands can be issued before DATA\n")
        #Tell the user how to enter email data.
        elif((msg_list[1] == "DATA:") or (msg_list[1] == "DATA")):
            rep = "214 Syntax: DATA:\nSome data\n.\nBe sure to terminate your data with a line containing only a period.\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"214 Syntax: DATA:\nSome data\n.\nBe sure to terminate your data with a line containing only a period.\n")
        #Tell the user how to terminate their session.
        elif(msg_list[1] == "QUIT"):
            rep = "214 Syntax: QUIT\nThis ends the connection and closes your client.\n"
            self.log_reply(rep, usr)
            usr.conn.sendall(b"214 Syntax: QUIT\nThis ends the connection and closes your client.\n")
        return

    #TTerminate session.
    def QUIT(self, msg, usr):
        #Send termination response, close the socket, and allow this thread to return.
        rep = "221 Closing transmission channel\n"
        self.log_reply(rep, usr)
        usr.conn.sendall(b"221 Closing transmission channel\n")
        usr.conn.close()
        usr.quit = True
        return
    pass

#Handle HTTP commands for viewing emails.
class HTTP_Handler:

    local_domain = None
    #Initialize HTTP thread.
    def __init__(self, conf):
        #Read the config file into memory.
        mutex.acquire()
        config = open(conf, "r")
        lines = config.readlines()
        config.close()
        mutex.release()
        local_domain = lines[0].strip
        tmp = lines[2]
        tmp_list = tmp.split("=")
        port = tmp_list[1]
        threads = []
        #Create a listener socket.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            myhost = socket.gethostname()
            self.HOST = socket.gethostbyname(myhost)
            s.bind((self.HOST, int(port)))
            #Continuously listen and accept connections, creating a new thread for each one.
            #Probably a good idea to implement a server-side command to allow the server to go offline when needed.
            while(True):
                s.listen()
                conn, addr = s.accept()
                usr = user("", conn, addr)
                print ("got HTTP connection from ", addr)
                t = threading.Thread(target = self.Handle_client, args = (usr,))
                threads.append(t)
                t.start()
            return

    #Log HTTP messages with a timestamp.
    def log(self, rep, frm, to):
        log_ent = str(datetime.now()) + " from: " + frm + " To: " + to + " " + rep + "\n"
        print(log_ent)
        mutex.acquire()
        lf = open(".server_log", "a")
        lf.write(log_ent)
        lf.close()
        mutex.release()
        return

    #User authenticattion.
    def AUTH(self, msg, usr):
        #Set up username and password prompts.
        code = b"334 "
        usr_tail = b"username"
        pass_tail = b"password"
        usr_tail = base64.b64encode(usr_tail)
        pass_tail = base64.b64encode(pass_tail)
        user_msg = code + usr_tail
        rep = codecs.decode(user_msg, "utf-8") + "\n"
        self.log(rep, self.HOST, usr.addr[0])
        #Send prompt and get the username.
        usr.conn.sendall(user_msg)
        name_64 = usr.conn.recv(1024)
        self.log(codecs.decode(name_64, "utf-8"), usr.addr[0], self.HOST)
        temp = base64.b64decode(name_64)
        name = codecs.decode(temp, "utf-8")
        name = name.strip()
        #Read the user password file into a list.
        mutex.acquire()
        usr_pass = open("db/.user_pass", "r+")
        lines = usr_pass.readlines()
        usr_pass.close()
        mutex.release()
        found = False
        pwrd = ""
        match = ""
        #Find the user.
        for line in lines:
            tmp = line.split("=")
            if((len(tmp) == 2) and (tmp[0] == name)):
               match = tmp[1].strip()
               found = True
               break
        if (found):
            #User was found, prompt them for the password.
            pass_msg = code + pass_tail
            rep = codecs.decode(pass_msg, "utf-8") + "\n"
            self.log(rep, self.HOST, usr.addr[0])
            usr.conn.sendall(pass_msg)
            #Get the password, decode, salt, and re-encode the password.
            pass_64 = usr.conn.recv(1024)
            self.log(codecs.decode(pass_64, "utf-8"), usr.addr[0], self.HOST)
            temp = base64.b64decode(pass_64)
            pwrd = codecs.decode(temp, "utf-8")
            salt = "447S21" + pwrd
            b_salt = codecs.encode(salt, "utf-8")
            b_salt = base64.b64encode(b_salt)
            salt_64 = codecs.decode(b_salt, "utf-8")
            #Compare the salted password to the stored value.
            if(salt_64 == match):
                #Password matched, let the user know and allow tthem to proceed.
                path ="db/" + name
                num_files = len([file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))])
                rep = "235 2.7.0 Authentication Succeeded: " + str(num_files) + " emails unread\n"
                self.log(rep, self.HOST, usr.addr[0])
                usr.conn.sendall(codecs.encode(rep, "utf-8"))
                usr.name = name
                usr.registered = True
            else:
                #Wrong password, abort mission!
                rep = "535 2.7.0 Authentication credentials invalid, terminating\n"
                self.log(rep, self.HOST, usr.addr[0])
                usr.conn.sendall(b"535 2.7.0 Authentication credentials invalid, terminating\n")
                usr.quit = True
                usr.conn.close()
        else:
            #This is a new user, generate a password, store it, and send it to the user, then terminate so the user can log in again.
            chars = string.digits + string.punctuation + string.ascii_letters
            r_string = "".join(random.choice(chars) for i in range(6))
            b_string = codecs.encode(r_string, "utf-8")
            salt = b"447S21" + b_string
            b_string = base64.b64encode(b_string)
            s_buf = b"330 " + b_string
            w_buf = codecs.encode(name, "utf-8") + b"=" + base64.b64encode(salt) + b"\n"
            mutex.acquire()
            usr_pass = open("db/.user_pass", "a")
            wr_buf = codecs.decode(w_buf, "utf-8")
            usr_pass.write(wr_buf)
            usr_pass.close()
            mutex.release()
            rep = codecs.decode(s_buf, "utf-8") + "\n"
            self.log(rep, self.HOST, usr.addr[0])
            usr.conn.sendall(s_buf)
            usr.quit = True
        return

    #Handle a client HTTP connection
    def Handle_client(self, usr):
        message = usr.conn.recv(1024)
        msg = codecs.decode(message, "utf-8")
        self.log(msg, usr.addr[0], self.HOST)
        msg_list = msg.split()
        while(usr.registered == False):
            #User is not registered, make sure they use AUTH.
            if(msg_list[0] == "AUTH"):
                self.AUTH(msg, usr)
                if(usr.registered == False):
                    usr.conn.close()
                    return
            else:
                #User must use AUTH first, let them know.
                rep = "503 Bad sequence of commands: expected AUTH\n"
                self.log_reply(rep, usr)
                usr.conn.sendall(b"503 Bad sequence of commands: expected AUTH\n")
                message = usr.conn.recv(1024)
                msg = codecs.decode(message, "utf-8")
                self.log(msg, usr.addr[0], self.HOST)
                msg_list = msg.split()
        message = usr.conn.recv(1024)
        msg = codecs.decode(message, "utf-8")
        self.log(msg, usr.addr[0], self.HOST)
        msg_list = msg.split()
        #Handle GET request.
        if((len(msg_list) == 7) and (msg_list[0] == "GET") and (msg_list[2] == "HTTP/1.1") and(msg_list[3] == "Host:") and (msg_list[5] == "Count:") and (int(msg_list[6]) > 0)):
            #Find all the user's unread emails.
            path = msg_list[1]
            host = msg_list[4]
            count = int(msg_list[6])
            num_files = len([file for file in os.listdir(path) if os.path.isfile(os.path.join(path, file))])
            if os.path.exists(path):
                #Send the OK with a tttimestamp showing when the most recent email was sent and the file type.
                path1 = path + "/" + str(num_files) + ".email"
                mutex.acquire()
                etime = os.path.getmtime(path1)
                mutex.release()
                mod = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(etime))
                send_buf = "HTTP/1.1 200 OK\nServer: 447.edu\nLast-Modified: " + mod + "\nCount: " + str(count) + "\nContent-Type: text/plain\n"
                self.log(send_buf, self.HOST, usr.addr[0])
                b_send = codecs.encode(send_buf, "utf-8")
                usr.conn.sendall(b_send)
                while((count > 0) and (num_files > 0)):
                    #For each file, read the contents into memory.
                    send_buf = "Message: " + str(num_files)
                    b_send = codecs.encode(send_buf, "utf-8")
                    self.log(send_buf, self.HOST, usr.addr[0])
                    usr.conn.sendall(b_send)
                    path1 = path + "/" + str(num_files) + ".email"
                    mutex.acquire()
                    fp = open(path1, "r")
                    f_data = fp.readlines()
                    fp.close()
                    mutex.release()
                    #Send the data line by line.
                    for line in f_data:
                        self.log(line, self.HOST, usr.addr[0])
                        b_data = codecs.encode(line, "utf-8")
                        usr.conn.sendall(b_data) 
                    
                    #Delete the file once sent to minimize usage of storage space.
                    mutex.acquire()
                    os.remove(path1)
                    mutex.release()
                    count -= 1
                    num_files -= 1
                    
                rep = "250 OK"
                self.log(rep, self.HOST, usr.addr[0])
                usr.conn.sendall(b'250 OK')
            else:
                rep = "404 Not Found: provided direcory cannot be found\n"
                self.log(rep, self.HOST, usr.addr[0])
                usr.conn.sendall(b'404 Not Found: provided direcory cannot be found\n')
        else:
            rep = "400 Bad Request: syntax error\n"
            self.log(rep, self.HOST, usr.addr[0])
            usr.conn.sendall(b'400 Bad Request: syntax error\n')
        usr.conn.close()
        return
    pass



