---- MODULE TokenRefreshReplay ----
EXTENDS Naturals
VARIABLES gen, replayed
Init == gen = 1 /\ replayed = FALSE
Rotate == gen < 3 /\ gen' = gen + 1 /\ UNCHANGED replayed
AcceptOldGen1 == gen = 3 /\ replayed = FALSE /\ replayed' = TRUE /\ UNCHANGED gen
Stay == replayed = TRUE /\ UNCHANGED <<gen, replayed>>
Next == Rotate \/ AcceptOldGen1 \/ Stay
NoTokenReplay == ~replayed
====
