from pymash import models


def test_matchup():
    white_function = models.Function('white_function_id', 'def add(x, y): return x + y')
    black_function = models.Function('black_function_id', 'def sub(x, y): return x - y')
    matchup = models.Matchup(white_function, black_function)
    assert matchup.white_function is white_function
    assert matchup.black_function is black_function
