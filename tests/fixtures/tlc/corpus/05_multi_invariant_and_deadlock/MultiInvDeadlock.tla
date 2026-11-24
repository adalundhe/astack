---- MODULE MultiInvDeadlock ----
EXTENDS Naturals
VARIABLES x, y
Init == x = 0 /\ y = 0
Inc == x = 0 /\ y = 0 /\ x' = 1 /\ y' = 1
BreakX == x = 1 /\ y = 1 /\ x' = 5 /\ y' = 1
BreakY == x = 1 /\ y = 1 /\ x' = 1 /\ y' = 5
StayY == y = 5 /\ UNCHANGED <<x, y>>
Next == Inc \/ BreakX \/ BreakY \/ StayY
SmallX == x < 4
SmallY == y < 4
====
