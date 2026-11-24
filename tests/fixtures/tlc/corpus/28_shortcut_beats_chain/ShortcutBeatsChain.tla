---- MODULE ShortcutBeatsChain ----
EXTENDS Naturals
VARIABLE step
Init == step = 0
Slow == step < 4 /\ step' = step + 1
Jump == step = 0 /\ step' = 4
Stay == step = 4 /\ step' = 4
Next == Slow \/ Jump \/ Stay
NoFour == step < 4
====
