---- MODULE InitInvariantBad ----
EXTENDS Naturals
VARIABLE x
Init == x = 9
Next == x' = x
NotNine == x # 9
====
