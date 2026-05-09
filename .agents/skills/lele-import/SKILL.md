---
name: lele-import
description: Convention for using dotted-path type aliases with the new_import_system custom import hook. Use when writing type hints, dataclass inheritance, isinstance checks, or any code that needs class references in projects using new_import_system.
---

# lele-import

Convention for working with the `new_import_system` custom import hook in any codebase.

## Why standard imports don't work

- `__init__.py` files must be **empty** (except top-level `install()` call) — re-exports aren't available
- Modules are **lazy** — accessed only on first attribute request
- Modules with `__call__` or a matching function name become **callable wrappers**
- Result: `from Package.Module import Name` does **not** work reliably for types

## The pattern

Use dotted-path aliases instead:

```python
ShortName = Package.Subpackage.Module.ClassName
```

It works because each `.` triggers the lazy-load chain, giving you the actual class object.

Place aliases at the top of your file, grouped by package.

## When to use

- Type hints (function signatures, variable annotations)
- Dataclass inheritance (`class MyConfig(Package.Module.ClassName)`)
- `isinstance()` checks
- Anywhere you need a reference to the class itself

## Diagnostic

If you get a `LazyModule` or `CallableModule` proxy instead of the expected class, you're not traversing far enough through the dotted path.
