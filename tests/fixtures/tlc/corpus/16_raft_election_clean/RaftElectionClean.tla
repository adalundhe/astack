---- MODULE RaftElectionClean ----
EXTENDS Naturals
VARIABLES role, term
Init == role = "follower" /\ term = 1
Timeout == role = "follower" /\ term < 2 /\ role' = "candidate" /\ term' = term + 1
WinQuorum == role = "candidate" /\ role' = "leader" /\ UNCHANGED term
StepDown == role = "leader" /\ role' = "follower" /\ UNCHANGED term
Stay == role = "follower" /\ term = 2 /\ UNCHANGED <<role, term>>
Next == Timeout \/ WinQuorum \/ StepDown \/ Stay
ValidTerm == term <= 2
====
