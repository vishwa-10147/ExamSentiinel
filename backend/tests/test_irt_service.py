from app.services.irt_service import IRTItem, IRTService


def test_irt_probability_and_information_are_bounded():
    service = IRTService()
    item = IRTItem("q1", discrimination=1.2, difficulty=0.0)
    assert 0.0 < service.probability(0.0, item) < 1.0
    assert service.information(0.0, item) > 0.0


def test_irt_estimate_moves_with_responses_and_has_interval():
    service = IRTService()
    item = IRTItem("q1", 1.0, 0.0)
    estimate = service.estimate([(item, True), (item, True)])
    assert estimate.theta > 0.0
    assert estimate.lower_bound < estimate.theta < estimate.upper_bound


def test_irt_selects_highest_information_unanswered_item():
    service = IRTService()
    items = [IRTItem("easy", 1.0, -3.0), IRTItem("target", 1.0, 0.0), IRTItem("hard", 1.0, 3.0)]
    selected = service.select_next(0.0, items, {"easy"})
    assert selected is not None
    assert selected.question_id == "target"
