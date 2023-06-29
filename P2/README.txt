This is just a rudimentary example of a SMTP system for demonstration purposes, it is by no means secure.
If you use it for anything other than goofing around, you do so at your own risk.
Server compilation:
python SMTP_Server.py Server.conf

-config file has no space between port and next domain and no brackets around domain,like this.
SELF_DOMAIN
PORT=
PORT=
DOMAIN
IP
PORT

Client compilation:
python SMTP_Client.py Sender.conf Receiver.conf
