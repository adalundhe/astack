---- MODULE CacheStaleRead ----
EXTENDS Naturals
VARIABLES db, cache
Init == db = 1 /\ cache = 1
WriteDbSkipEvict == db = 1 /\ db' = 2 /\ UNCHANGED cache
TtlRefresh == db = 2 /\ cache = 1 /\ cache' = 2 /\ UNCHANGED db
Stay == db = 2 /\ cache = 2 /\ UNCHANGED <<db, cache>>
Next == WriteDbSkipEvict \/ TtlRefresh \/ Stay
CacheCoherence == cache = db
====
