---- MODULE SagaOrphanCharge ----
VARIABLES charged, shipped, aborted
Init == charged = FALSE /\ shipped = FALSE /\ aborted = FALSE
Charge == ~charged /\ ~aborted /\ charged' = TRUE /\ UNCHANGED <<shipped, aborted>>
AbortWithoutRefund == charged /\ ~shipped /\ ~aborted /\ aborted' = TRUE /\ UNCHANGED <<charged, shipped>>
Stay == aborted /\ UNCHANGED <<charged, shipped, aborted>>
Next == Charge \/ AbortWithoutRefund \/ Stay
NoOrphanCharge == ~(aborted /\ charged)
====
