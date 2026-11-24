---- MODULE MultilineRecords ----
EXTENDS Naturals
VARIABLE cfg
Init == cfg = [host |-> "alpha", path |-> "/tmp/a", retries |-> 0, ok |-> TRUE]
Corrupt == cfg.ok = TRUE /\ cfg' = [host |-> "alpha", path |-> "/etc/bad", retries |-> 3, ok |-> FALSE]
Stay == cfg.ok = FALSE /\ cfg' = cfg
Next == Corrupt \/ Stay
PathSafe == cfg.ok = TRUE
====
