import json

# Manually labeled "Golden Set" for Dive Bar Sentiment Evaluation
# Labels: 1 (Negative), 2 (Poor), 3 (Neutral), 4 (Good), 5 (Excellent)
# Focus: Sarcasm, "Divey" compliments (dirty but good), and genuine complaints.

golden_set = [
    # Positive Dive Reviews (Tricky)
    {"text": "Total dive. Sticky floors, smells like bleach. Best night of my life.", "label": 5},
    {"text": "Don't come here if you want fancy cocktails. Cash only. Perfect.", "label": 5},
    {"text": "It's a hole in the wall. The bathroom is scary. I love it.", "label": 4},
    {"text": "Bartender ignored me for 10 minutes. 10/10 experience.", "label": 5}, # Sarcasm/Cult
    
    # Negative Dive Reviews (Genuine)
    {"text": "Disgusting. Saw a roach.", "label": 1},
    {"text": "Rude staff kicked us out for no reason.", "label": 1},
    {"text": "Beer was warm and flat.", "label": 1},
    
    # Neutral / Mixed
    {"text": "It's okay for a quick beer. Nothing special.", "label": 3},
    {"text": "Cheap drinks but way too loud.", "label": 3},
    
    # Positive Standard Reviews
    {"text": "Great service and amazing burger!", "label": 5},
    {"text": "Lovely atmosphere, very clean.", "label": 5}
]

with open("golden_set.json", "w") as f:
    json.dump(golden_set, f, indent=2)

print("Created golden_set.json with", len(golden_set), "examples.")

