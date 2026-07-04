from pgai_patient_bot.scenarios import default_scenario_path, load_scenarios


def test_at_least_ten_scenarios() -> None:
    assert len(load_scenarios()) >= 10


def test_scenario_ids_are_unique() -> None:
    ids = [scenario.id for scenario in load_scenarios()]
    assert len(ids) == len(set(ids))


def test_each_scenario_has_opening_line() -> None:
    for scenario in load_scenarios():
        assert scenario.opening_line.strip()


def test_default_scenarios_are_packaged() -> None:
    assert default_scenario_path().exists()
