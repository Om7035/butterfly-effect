---
name: Causal chain validation report
about: Report when a causal chain is wrong, missing an effect, or has incorrect timing
title: "validation: [EVENT] â€” [what was wrong]"
labels: validation
assignees: ''
---

## The question you asked

```
[paste exact question here]
```

## What the system returned

```
[paste chain output or describe it]
```

## What was wrong

- [ ] Missing effect that should be in the chain
- [ ] Effect that shouldn't be in the chain (false positive)
- [ ] Wrong timing â€” latency_hours is off
- [ ] Wrong confidence score
- [ ] Wrong domain classification
- [ ] Other: 

## What the correct chain should look like

```
[correct hop]: [cause] â”€â”€â–¶ [effect]  at [timing]  confidence ~[X]
```

**Evidence supporting the correct chain:**
<!-- Link to FRED data, academic paper, news article, etc. -->

## Historical reference

Did this event actually happen? If so, what did we observe?

- Event date: 
- Observed outcome: 
- Source: 

## Severity

- [ ] Minor â€” timing is off by <50%
- [ ] Moderate â€” missing a significant 2nd/3rd order effect
- [ ] Major â€” the primary chain is wrong
- [ ] Critical â€” the system returned the opposite of what happened
