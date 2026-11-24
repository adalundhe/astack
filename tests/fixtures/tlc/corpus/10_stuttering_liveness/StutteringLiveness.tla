---- MODULE StutteringLiveness ----
EXTENDS Naturals
VARIABLE x
Init == x = 0
Advance == x = 0 /\ x' = 1
Stay == x = 1 /\ x' = 1
Next == Advance \/ Stay
Spec == Init /\ [][Next]_x
EventuallyOne == <>(x = 1)
====
