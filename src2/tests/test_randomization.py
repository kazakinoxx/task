from src2.utils.randomization import random_number_bm, sample_delay_uniform_centered, shuffle


def test_random_number_bm_stays_in_range():
    for _ in range(200):
        val = random_number_bm(10, 20)
        assert 10 <= val <= 20


def test_sample_delay_uniform_centered_clamps_at_zero():
    for _ in range(200):
        val = sample_delay_uniform_centered(10, 25)
        assert 0 <= val <= 35


def test_shuffle_preserves_elements_and_does_not_mutate_input():
    original = [1, 2, 3, 4, 5]
    result = shuffle(original)
    assert sorted(result) == sorted(original)
    assert original == [1, 2, 3, 4, 5]
