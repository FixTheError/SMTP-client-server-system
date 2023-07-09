This is just a rudimentary example of a SMTP system for demonstration purposes, it is by no means secure.
If you use it for anything other than goofing around, you do so at your own risk.
There is a lot of room for improvement. I will fix the bugs and redundancies once I have a chance to do so.
My laptop keeps throwing a blue screen of death just about every day, so I need to fix that before I do any more coding on it.
Hopefully I'll at least have another menial job soon, then I'll be able to stop living like I'm nearly homeless and buy a WiFi adapter or a new NIC for my desktop,
so I'll have a backup computer if something goes horribly wrong while I try to fix my laptop.
The struggle is very real, and it may slow things down, but it's not going to stop me.
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
