# [Feature Name] Test Fixtures

> Ground truth for tests. Copy these into actual test files.
> Note: In TDD mode, SPEC.md's "Tests to Write First" sections are the primary test data source. This file is generated only when explicit fixture definitions add value beyond what the spec provides.

## Location

Test fixtures should live in:
```
path/to/fixtures.py
```

## Imports

```python
import pytest
from path.to.models import Model
```

---

## [Model/Context Name]

```python
@pytest.fixture
def sample_[name]() -> [Type]:
    """Sample [name] for testing."""
    return [Type](
        field1=value1,
        field2=value2,
    )
```
