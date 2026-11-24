---- MODULE ActionPropertyBad ----
EXTENDS Naturals
VARIABLE x
Init == x = 1
Drop == x = 1 /\ x' = 0
Stay == x = 0 /\ x' = 0
Next == Drop \/ Stay
Spec == Init /\ [][Next]_x
Monotonic == [][x' >= x]_x
====
