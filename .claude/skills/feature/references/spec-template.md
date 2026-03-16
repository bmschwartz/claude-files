# Feature Specification: [Feature Name]

## Feature Overview
[Concise description of the feature and its purpose]

## Codebase Context

### Similar Implementations
- `path/to/similar/feature.py` - [How it's relevant]
- `path/to/pattern/example.py` - [What we're reusing]

### Patterns to Follow
- [Pattern name] from `path/to/example`

### Constraints Discovered
- [Constraint from existing architecture]

## Discovery Summary

### Discovery: Codebase Exploration
*Key findings from exploration:*
- [Finding 1]
- [Finding 2]

### Discovery: Requirements
Q: [Question asked]
A: [Answer provided]
*Requirement: [What we learned]*

## Key Insights

- [Insight about architectural decision]
- [Insight about trade-offs made]
- [Insight about codebase patterns]

## Risk Assessment

| Risk Type | Level | Details | Mitigation |
|-----------|-------|---------|------------|
| Pattern Deviation | [Level] | [Details] | [Strategy] |
| Dependency Impact | [Level] | [Details] | [Strategy] |
| Testing Coverage | [Level] | [Details] | [Strategy] |

## Requirements

### Functional Requirements
- [ ] Requirement 1 (Priority: High/Med/Low)
- [ ] Requirement 2 (Priority: High/Med/Low)

### Non-Functional Requirements
- [ ] Performance: [Specific metrics]
- [ ] Security: [Specific requirements]
- [ ] Scalability: [Expected load]

## Implementation Plan

### Phase 1: [Core Functionality]
**Complexity:** Low/Medium/High
**Dependencies:** [What must be completed first]

1. `path/to/file.py`
   - [ ] Add function X
   - [ ] Update method Y
2. `path/to/newfile.py`
   - [ ] Implement class Z

#### Tests to Write First
- [ ] [Test description] (Impact: HIGH/MEDIUM/LOW)
- [ ] [Test description] (Impact: HIGH/MEDIUM/LOW)

> Target: ≥50% HIGH impact, ≤25% LOW impact

#### Refactoring Notes
- [Cleanup expected after green]

### Phase 2: [Enhancements/Edge Cases]
**Complexity:** Low/Medium/High
**Dependencies:** [Phase 1 completion]

#### Tests to Write First
- [ ] [Test description] (Impact: HIGH/MEDIUM/LOW)

#### Refactoring Notes
- [Cleanup expected after green]

## Testing Strategy

### Unit Tests
- [ ] Test case 1: [Description]
- [ ] Test case 2: [Description]

### Integration Tests
- [ ] Test scenario 1: [Description]

### Manual Testing Checklist
- [ ] User workflow 1
- [ ] Edge case handling

## Success Criteria
- [ ] All functional requirements implemented
- [ ] All tests passing
- [ ] Performance metrics met: [Specific metrics]
- [ ] No regression in existing functionality
- [ ] Code review complete

## Rollback Plan
1. Revert commits: [Will be listed during implementation]
2. Database changes: [If applicable]
3. Configuration rollback: [If applicable]

## Iteration Log
*Track changes to the spec during implementation:*

| Date | Change | Reason |
|------|--------|--------|
| [Date] | Initial spec | - |
