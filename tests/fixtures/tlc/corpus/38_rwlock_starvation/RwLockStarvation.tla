---- MODULE RwLockStarvation ----
VARIABLES readers, writer
Init == readers = 0 /\ writer = "waiting"
ReaderEnter == readers = 0 /\ writer = "waiting" /\ readers' = 1 /\ UNCHANGED writer
ReaderOverlap == readers = 1 /\ writer = "waiting" /\ readers' = 2 /\ UNCHANGED writer
ReaderLeave == readers = 2 /\ writer = "waiting" /\ readers' = 1 /\ UNCHANGED writer
Next == ReaderEnter \/ ReaderOverlap \/ ReaderLeave
Spec == Init /\ [][Next]_<<readers, writer>> /\ WF_<<readers, writer>>(Next)
WriterEventuallyRuns == <>(writer = "active")
====
