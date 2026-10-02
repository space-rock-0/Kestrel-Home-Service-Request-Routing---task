# plugins/

Drop a `.py` file (or a package folder with `__init__.py`) here. It loads at startup. It needs one function:

```python
def register(registry):
    registry.register(MyTool())
```

`data_summary.py` is a working example. A plugin that fails to import is listed under `load_errors` at `GET /api/extensions` and does not stop the app.

Contracts live in `kestrel/extensions/base.py`: `Tool`, `Command`, `Skill`, `Workflow`, `Agent`.
