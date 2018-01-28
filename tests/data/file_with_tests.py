def select_even(numbers):
    result = []
    for a_number in numbers:
        if a_number % 2 == 0:
            result.append(a_number)
    return result
