---- MODULE RateLimiterOverflow ----
EXTENDS Naturals
VARIABLE tokens
Init == tokens = 2
Consume == tokens = 2 /\ tokens' = 1
RefillFromOne == tokens = 1 /\ tokens' = 2
Refill == tokens = 2 /\ tokens' = 3
UncappedRefill == tokens = 3 /\ tokens' = 5
Stay == tokens = 5 /\ tokens' = 5
Next == Consume \/ RefillFromOne \/ Refill \/ UncappedRefill \/ Stay
BucketBounded == tokens <= 4
====
