---- MODULE BarrierDeadlock ----
VARIABLES w1, w2
Init == w1 = "run" /\ w2 = "run"
W1Arrive == w1 = "run" /\ w1' = "wait" /\ UNCHANGED w2
W2Crash == w2 = "run" /\ w2' = "crashed" /\ UNCHANGED w1
Release == w1 = "wait" /\ w2 = "wait" /\ w1' = "run" /\ w2' = "run"
Next == W1Arrive \/ W2Crash \/ Release
====
