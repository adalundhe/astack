---- MODULE CounterClean ----
EXTENDS Naturals
VARIABLE x
Init == x = 0
Inc == x < 3 /\ x' = x + 1
Reset == x = 3 /\ x' = 0
Next == Inc \/ Reset
Safe == x <= 3
====
