---- MODULE AdversarialStrings ----
VARIABLE tag
Init == tag = "[*] --> %%init"
Mid == tag = "[*] --> %%init" /\ tag' = "quote \"here\" \\"
Bad == tag = "quote \"here\" \\" /\ tag' = "end --> state"
Stay == tag = "end --> state" /\ tag' = tag
Next == Mid \/ Bad \/ Stay
SafeTag == tag # "end --> state"
====
