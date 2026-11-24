---- MODULE SagaClean ----
VARIABLE saga
Init == saga = "started"
Reserve == saga = "started" /\ saga' = "reserved"
Charge == saga = "reserved" /\ saga' = "charged"
Ship == saga = "charged" /\ saga' = "shipped"
ShipFailRefund == saga = "charged" /\ saga' = "refunded"
ReleaseStock == saga = "refunded" /\ saga' = "aborted"
ChargeFailRelease == saga = "reserved" /\ saga' = "aborted"
Done == saga \in {"shipped", "aborted"} /\ saga' = saga
Next == Reserve \/ Charge \/ Ship \/ ShipFailRefund \/ ReleaseStock \/ ChargeFailRelease \/ Done
ValidSaga == saga \in {"started", "reserved", "charged", "shipped", "refunded", "aborted"}
====
