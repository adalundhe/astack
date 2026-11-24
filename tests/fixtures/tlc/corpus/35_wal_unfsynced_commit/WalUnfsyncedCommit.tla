---- MODULE WalUnfsyncedCommit ----
EXTENDS Naturals
VARIABLES acked, disk, lost
Init == acked = 0 /\ disk = 0 /\ lost = FALSE
AckBeforeFsync == acked = 0 /\ acked' = 1 /\ UNCHANGED <<disk, lost>>
Fsync == acked = 1 /\ disk = 0 /\ ~lost /\ disk' = 1 /\ UNCHANGED <<acked, lost>>
CrashLoseAcked == acked = 1 /\ disk = 0 /\ ~lost /\ lost' = TRUE /\ UNCHANGED <<acked, disk>>
Stay == (disk = 1 \/ lost) /\ UNCHANGED <<acked, disk, lost>>
Next == AckBeforeFsync \/ Fsync \/ CrashLoseAcked \/ Stay
DurableCommit == ~lost
====
