from cbsrmt_api.presentation import normalize_episode_title, normalize_episode_titles


def test_normalize_episode_title_moves_trailing_article():
    assert normalize_episode_title("Old Ones Are Hard to Kill [The]") == "The Old Ones Are Hard to Kill"
    assert normalize_episode_title("Question of Identity [A]") == "A Question of Identity"
    assert normalize_episode_title("Appointment with Death [An]") == "An Appointment with Death"


def test_normalize_episode_title_leaves_other_titles_unchanged():
    assert normalize_episode_title("The Deadly Process") == "The Deadly Process"
    assert normalize_episode_title("Something [Else]") == "Something [Else]"


def test_normalize_episode_titles_recurses_through_api_payload():
    payload = {
        "data": [
            {"episode_name": "Old Ones Are Hard to Kill [The]"},
            {
                "nested": {
                    "episode_name": "Question of Identity [A]",
                    "other": "unchanged",
                }
            },
        ]
    }

    assert normalize_episode_titles(payload) == {
        "data": [
            {"episode_name": "The Old Ones Are Hard to Kill"},
            {
                "nested": {
                    "episode_name": "A Question of Identity",
                    "other": "unchanged",
                }
            },
        ]
    }
