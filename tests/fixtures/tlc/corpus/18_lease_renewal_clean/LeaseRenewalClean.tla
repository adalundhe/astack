---- MODULE LeaseRenewalClean ----
VARIABLE lease
Init == lease = "free"
Acquire == lease = "free" /\ lease' = "held"
StartRenew == lease = "held" /\ lease' = "renewing"
RenewOk == lease = "renewing" /\ lease' = "held"
RenewTimeout == lease = "renewing" /\ lease' = "expired"
Reclaim == lease = "expired" /\ lease' = "free"
Next == Acquire \/ StartRenew \/ RenewOk \/ RenewTimeout \/ Reclaim
ValidState == lease \in {"free", "held", "renewing", "expired"}
====
