---- MODULE LeaseStaleWrite ----
EXTENDS Naturals
VARIABLES holder, epoch, stale_write
Init == holder = "a" /\ epoch = 1 /\ stale_write = FALSE
ExpireA == holder = "a" /\ holder' = "none" /\ UNCHANGED <<epoch, stale_write>>
GrantB == holder = "none" /\ holder' = "b" /\ epoch' = 2 /\ UNCHANGED stale_write
UnfencedWriteA == holder = "b" /\ stale_write = FALSE /\ stale_write' = TRUE /\ UNCHANGED <<holder, epoch>>
Stay == stale_write = TRUE /\ UNCHANGED <<holder, epoch, stale_write>>
Next == ExpireA \/ GrantB \/ UnfencedWriteA \/ Stay
LinearizableWrite == ~stale_write
====
