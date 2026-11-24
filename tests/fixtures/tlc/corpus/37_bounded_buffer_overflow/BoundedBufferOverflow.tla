---- MODULE BoundedBufferOverflow ----
EXTENDS Naturals
VARIABLE count
Init == count = 0
Produce == count < 4 /\ count' = count + 1
Consume == count > 0 /\ count' = count - 1
Next == Produce \/ Consume
CapThree == count <= 3
====
