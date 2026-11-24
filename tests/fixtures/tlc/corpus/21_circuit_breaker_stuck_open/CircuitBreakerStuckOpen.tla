---- MODULE CircuitBreakerStuckOpen ----
VARIABLE cb
Init == cb = "closed"
Trip == cb = "closed" /\ cb' = "open"
RejectCall == cb = "open" /\ cb' = "open"
Next == Trip \/ RejectCall
Spec == Init /\ [][Next]_cb /\ WF_cb(Next)
EventuallyRecovers == [](cb = "open" => <>(cb = "closed"))
====
