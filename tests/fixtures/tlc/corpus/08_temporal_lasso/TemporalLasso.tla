---- MODULE TemporalLasso ----
EXTENDS Naturals
VARIABLE x
Init == x = 0
Up == x < 2 /\ x' = x + 1
Back == x = 2 /\ x' = 1
Next == Up \/ Back
Spec == Init /\ [][Next]_x /\ WF_x(Next)
ReachesThree == <>(x = 3)
====
