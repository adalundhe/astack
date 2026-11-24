---- MODULE MultiInitShortest ----
EXTENDS Naturals
VARIABLES seed, v
Init == (seed = "a" /\ v = 0) \/ (seed = "b" /\ v = 0)
SlowA == seed = "a" /\ v < 3 /\ v' = v + 1 /\ UNCHANGED seed
FastB == seed = "b" /\ v = 0 /\ v' = 3 /\ UNCHANGED seed
Stay == v = 3 /\ UNCHANGED <<seed, v>>
Next == SlowA \/ FastB \/ Stay
BoundV == v < 3
====
