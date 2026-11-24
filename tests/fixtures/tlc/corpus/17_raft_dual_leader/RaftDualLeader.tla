---- MODULE RaftDualLeader ----
EXTENDS Naturals, FiniteSets
VARIABLE leaders
Init == leaders = {}
ElectN1 == leaders = {} /\ leaders' = {"n1"}
StaleVoteElectN2 == leaders = {"n1"} /\ leaders' = {"n1", "n2"}
Stay == leaders = {"n1", "n2"} /\ leaders' = leaders
Next == ElectN1 \/ StaleVoteElectN2 \/ Stay
ElectionSafety == Cardinality(leaders) <= 1
====
