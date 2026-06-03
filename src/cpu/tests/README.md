# CPU tests

cocotb unit tests for cpu modules. runs against verilator using transpiled SV in `target/`.

## run

```bash
uv run pytest test.py
# or
pytest test.py
```

## add a test

1. in `test.py`, add a function:

```python
def test_cpu_foo():
    run_test("cpu_foo")
```

2. create `test_cpu_foo.py` with one or more `@cocotb.test()` functions.
