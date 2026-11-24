---- MODULE TcpHandshakeClean ----
VARIABLE s
Init == s = "CLOSED"
PassiveOpen == s = "CLOSED" /\ s' = "LISTEN"
RecvSYN == s = "LISTEN" /\ s' = "SYN_RCVD"
RecvACK == s = "SYN_RCVD" /\ s' = "ESTABLISHED"
Close == s = "ESTABLISHED" /\ s' = "FIN_WAIT"
RecvFINACK == s = "FIN_WAIT" /\ s' = "CLOSED"
Next == PassiveOpen \/ RecvSYN \/ RecvACK \/ Close \/ RecvFINACK
ValidTcp == s \in {"CLOSED", "LISTEN", "SYN_RCVD", "ESTABLISHED", "FIN_WAIT"}
====
