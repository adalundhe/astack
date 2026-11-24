---- MODULE BoundedBufferClean ----
EXTENDS Naturals
VARIABLE count
Init == count = 0
Produce == count < 3 /\ count' = count + 1
Consume == count > 0 /\ count' = count - 1
Next == Produce \/ Consume
InBounds == count >= 0 /\ count <= 3
====
