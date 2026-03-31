---
name: Causal chain validation report
about: Report when a causal chain is wrong, missing an effect, or has incorrect timing
title: "validation: [EVENT] — [what was wrong]"
labels: validation
assignees: ''
---

## The question you asked
<!-- Paste the exact question you typed -->

## What the system returned
<!-- Paste the chain output or describe it -->

## What was wrong
<!-- Be specific: wrong hop, wrong timing, missing effect, wrong confidence, etc. -->

- [ ] Missing effect that should be in the chain
- [ ] Effect that shouldn't be in the chain (false positive)
- [ ] Wrong timing (latency_hours is off)
- [ ] Wrong confidence score
- [ ] Wrong domain classification
- [ ] Other: 

## What the correct chain should look like
<!-- If you know the correct answer, describe it here -->

**Correct hop:** [cause] → [effect] at [timing] with [confidence]

**Evidence:** Link to source that supports the correct chain (FRED data, academic paper, news article, etc.)

## Historical reference
<!-- Did this event actually happen? If so, what did we observe? -->

- Event date: 
- Observed outcome: 
- Source: 

## Severity
<!-- How wrong is it? -->
- [ ] Minor — timing is off by <50%
- [ ] Moderate — missing a significant 2nd/3rd order effect
- [ ] Major — the primary chain is wrong
- [ ] Critical — the system returned the opposite of what happened
