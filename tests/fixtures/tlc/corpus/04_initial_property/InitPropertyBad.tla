---- MODULE InitPropertyBad ----
EXTENDS Naturals
VARIABLE x
Init == x = 9
Next == x' = x
Spec == Init /\ [][Next]_x
InitZero == x = 0
====
