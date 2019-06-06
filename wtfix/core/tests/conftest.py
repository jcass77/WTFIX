import json

import pytest


@pytest.fixture(scope="session")
def encoded_dict_sample():
    return json.dumps(
        {
            35: "a",
            2: "b",
            539: [
                {
                    524: "a",
                    525: "aa",
                    538: "aaa",
                    804: [{545: "c", 805: "cc"}, {545: "d", 805: "dd"}],
                },
                {
                    524: "b",
                    525: "bb",
                    538: "bbb",
                    804: [{545: "e", 805: "ee"}, {545: "f", 805: "ff"}],
                },
            ],
            3: "c",
            "group_templates": {
                539: {"*": [524, 525, 538, 804]},
                804: {"*": [545, 805]},
            },
        }
    )


@pytest.fixture(scope="session")
def encoded_list_sample():
    return json.dumps(
        [
            (35, "a"),
            (2, "b"),
            (539, "2"),
            (524, "a"),
            (525, "aa"),
            (538, "aaa"),
            (804, "2"),
            (545, "c"),
            (805, "cc"),
            (545, "d"),
            (805, "dd"),
            (524, "b"),
            (525, "bb"),
            (538, "bbb"),
            (804, "2"),
            (545, "e"),
            (805, "ee"),
            (545, "f"),
            (805, "ff"),
            (3, "c"),
        ]
    )
