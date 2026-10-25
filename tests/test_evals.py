from evals import run_evals


def test_twelve_cases_all_pass_in_demo_mode():
    out = run_evals.run_all()
    assert out["total"] == 12
    failed = [(r["id"], r["problems"]) for r in out["results"] if not r["passed"]]
    assert not failed
    assert out["pass_rate"] == 100.0
