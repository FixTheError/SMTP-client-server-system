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
