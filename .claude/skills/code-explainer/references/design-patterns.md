# Design Patterns Catalog

Reference when identifying patterns in code. Each entry lists detection cues so you can spot the pattern quickly.

## Table of Contents
- [Creational](#creational)
- [Structural](#structural)
- [Behavioral](#behavioral)
- [Architectural](#architectural)
- [Functional / Pythonic](#functional--pythonic)

---

## Creational

### Singleton
**Intent:** Ensure only one instance of a class exists.
**Detection cues:** `_instance` class variable; `__new__` override; `instance()` class method; module-level global object.

### Factory Method
**Intent:** Delegate object creation to subclasses or a dedicated function.
**Detection cues:** Function named `create_*`, `make_*`, or `build_*`; returns different concrete types based on a parameter; `if type == "x": return X()`.

### Builder
**Intent:** Construct a complex object step by step using chained calls.
**Detection cues:** Methods that return `self`; `.set_*()` / `.with_*()` chains ending in `.build()`.

### Dependency Injection
**Intent:** Pass dependencies in rather than creating them internally.
**Detection cues:** Constructor accepts interfaces/callables as parameters (`def __init__(self, db, logger)`); default parameter is `None` with late binding.

---

## Structural

### Decorator (Pattern)
**Intent:** Wrap an object to add behaviour without changing its interface.
**Detection cues:** Class wraps another object of the same type; Python `@functools.wraps`; wrapper functions that call the original and augment the result.
> Note: Distinguish from Python's `@decorator` syntax, which is the same pattern applied to functions.

### Facade
**Intent:** Provide a simple interface over a complex subsystem.
**Detection cues:** One public function/class that calls many internal modules; hides implementation details; the caller never touches the subsystem directly.

### Adapter
**Intent:** Convert one interface to another.
**Detection cues:** Class wraps a third-party object and exposes a different method signature; often named `*Adapter`, `*Wrapper`, or `*Bridge`.

### Composite
**Intent:** Treat individual objects and compositions uniformly.
**Detection cues:** Tree structures; a class holds a list of objects of the same type; recursive `render()` / `execute()` / `size()` methods.

### Proxy
**Intent:** Control access to another object (lazy loading, caching, auth checks).
**Detection cues:** Object that wraps another and intercepts calls; `__getattr__` forwarding; `@cached_property`; lazy initialisation pattern.

---

## Behavioral

### Strategy
**Intent:** Swap algorithms at runtime without changing the caller.
**Detection cues:** Constructor or function accepts a callable/object that implements an operation (`sort_fn`, `validator`, `formatter`); the concrete algorithm is injected, not hardcoded.

### Observer / Event
**Intent:** Notify multiple subscribers when state changes.
**Detection cues:** `subscribe()` / `on()` / `add_listener()` methods; list of callbacks iterated on change; `emit()` / `notify()` / `dispatch()` calls.

### Command
**Intent:** Encapsulate a request as an object for queuing, logging, or undo.
**Detection cues:** Objects with a single `execute()` method; command queue or history list; `undo()` paired with `execute()`.

### Chain of Responsibility
**Intent:** Pass a request along a chain of handlers until one handles it.
**Detection cues:** Each handler holds a reference to the next; `handle(request)` either processes or forwards; middleware pipelines.

### Template Method
**Intent:** Define the skeleton of an algorithm in a base class; let subclasses fill in steps.
**Detection cues:** Base class method calls `self._step_one()`, `self._step_two()` etc.; abstract methods in base class; subclasses override only specific steps.

### Iterator
**Intent:** Traverse a collection without exposing its structure.
**Detection cues:** `__iter__` / `__next__`; `yield` in a generator; custom `for`-compatible objects.

---

## Architectural

### Repository
**Intent:** Abstract data access behind a collection-like interface.
**Detection cues:** Class named `*Repository` or `*Store` with `find_by_*`, `save()`, `delete()` methods; hides SQL/ORM details from business logic.

### Service Layer
**Intent:** Coordinate domain logic and keep it out of controllers/handlers.
**Detection cues:** Class/module named `*Service` called by a thin controller; handles transactions, orchestrates multiple domain objects.

### Orchestrator
**Intent:** Coordinate multiple agents or services in a defined sequence.
**Detection cues:** Central function/class calls other agents sequentially or in parallel; collects and merges results; owns error handling for the pipeline.

### Guard Clause (early return)
**Intent:** Flatten nesting by returning early on invalid conditions.
**Detection cues:** Multiple `if not x: raise/return` at the top of a function before the main logic; avoids deeply nested `if/else`.

---

## Functional / Pythonic

### Pipeline
**Intent:** Pass data through a series of transforms.
**Detection cues:** Chain of function calls where output of one feeds the next; `reduce`, `map`, `filter` chains; generator pipelines.

### Null Object
**Intent:** Use a do-nothing object instead of `None` checks.
**Detection cues:** `NullLogger`, `NoopCache`, or similar objects with empty method implementations; eliminates `if obj is not None` guards.

### Context Manager
**Intent:** Guarantee setup and teardown around a block of code.
**Detection cues:** `with` statement; `__enter__` / `__exit__` methods; `@contextmanager` decorator with `yield`.

### Mixin
**Intent:** Add reusable behaviour to classes without inheritance hierarchy constraints.
**Detection cues:** Class named `*Mixin` with no `__init__`; used in multiple-inheritance `class Foo(BaseMixin, LogMixin)`.
