# Candidate-v9 Confirmatory Failure Taxonomy for Candidate-v10

Classification: `HISTORICAL_DIAGNOSTIC_ONLY`

Observed false-abstention cases: **10**.

## Root-cause counts

- `relation_abstraction`: 10
- `typed_value_inference`: 1

## Failure cases

### CV9-CONF-A-066
- query: Which morning meal is Gwen Mori's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Mori's regular breakfast is fruit salad.

### CV9-CONF-A-131
- query: Which state is Umar Garcia's permit in now?
- root causes: relation_abstraction, typed_value_inference
- relations: ['status']
- value types: ['status']
- relevant evidence: Umar Garcia's permit is currently reviewing.

### CV9-CONF-A-162
- query: Which morning meal is Gwen Arden's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Arden's regular breakfast is rye toast.

### CV9-CONF-A-114
- query: Which morning meal is Gwen Olsen's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Olsen's regular breakfast is savory pancakes.

### CV9-CONF-A-018
- query: Which morning meal is Gwen Kovac's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Kovac's regular breakfast is bean toast.

### CV9-CONF-A-090
- query: Which morning meal is Gwen Fischer's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Fischer's regular breakfast is corn porridge.

### CV9-CONF-A-186
- query: Which morning meal is Gwen Jensen's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Jensen's regular breakfast is fruit yogurt.

### CV9-CONF-A-210
- query: Which morning meal is Gwen Costa's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Costa's regular breakfast is rice porridge.

### CV9-CONF-A-042
- query: Which morning meal is Gwen Dahl's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Dahl's regular breakfast is noodle bowl.

### CV9-CONF-A-138
- query: Which morning meal is Gwen Hale's regular choice?
- root causes: relation_abstraction
- relations: ['preference']
- value types: ['food']
- relevant evidence: Gwen Hale's regular breakfast is oatmeal.

## Interpretation rule

These cases are historical diagnosis only. Their literal strings, answers, case IDs, and exact constructions are forbidden from Candidate-v10 protected/confirmatory/final generation and inference hardcoding.
