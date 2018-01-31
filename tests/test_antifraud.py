from pymash import antifraud


def test_antifraud():
    cop = antifraud.Cop()
    cop.add_game(game1)
    cop.add_game(game2)
    assert cop.is_fraud(game3)