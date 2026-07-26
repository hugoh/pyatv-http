from pyatv_http.stats import StatsStore


def test_record_appends_to_recent():
    store = StatsStore(history_size=10)

    store.record("living_room", "get_power_state", ok=True, detail="on")

    recent = store.recent()
    assert len(recent) == 1
    assert recent[0].device == "living_room"
    assert recent[0].command == "get_power_state"
    assert recent[0].ok is True
    assert recent[0].detail == "on"


def test_recent_is_most_recent_first():
    store = StatsStore(history_size=10)

    store.record("living_room", "get_power_state", ok=True, detail="on")
    store.record("bedroom", "set_power_state", ok=True, detail="off")

    recent = store.recent()
    assert [r.device for r in recent] == ["bedroom", "living_room"]


def test_history_is_bounded_by_history_size():
    store = StatsStore(history_size=2)

    store.record("living_room", "get_power_state", ok=True, detail="on")
    store.record("living_room", "get_power_state", ok=True, detail="off")
    store.record("living_room", "get_power_state", ok=True, detail="on")

    recent = store.recent()
    assert len(recent) == 2
    assert recent[0].detail == "on"
    assert recent[1].detail == "off"


def test_totals_tracks_success_and_error_per_device():
    store = StatsStore(history_size=10)

    store.record("living_room", "get_power_state", ok=True, detail="on")
    store.record("living_room", "set_power_state", ok=False, detail="boom")
    store.record("bedroom", "get_power_state", ok=True, detail="off")

    totals = store.totals()
    assert totals["living_room"] == {"success": 1, "error": 1}
    assert totals["bedroom"] == {"success": 1, "error": 0}
    assert totals["_global"] == {"success": 2, "error": 1}


def test_totals_empty_store():
    store = StatsStore(history_size=10)

    assert store.totals() == {"_global": {"success": 0, "error": 0}}
