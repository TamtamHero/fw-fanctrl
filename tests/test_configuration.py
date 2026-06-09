import pytest
from jsonschema.exceptions import ValidationError

from fw_fanctrl.Configuration import Configuration


def parse_config(raw_config):
    configuration = Configuration.__new__(Configuration)
    return configuration.parse(raw_config)


def test_two_decimal_temperature_threshold_is_valid():
    config = parse_config(
        """
        {
            "defaultStrategy": "hotonleg",
            "strategyOnDischarging": "",
            "strategies": {
                "hotonleg": {
                    "speedCurve": [
                        {"temp": 30, "speed": 0},
                        {"temp": 64.99, "speed": 50}
                    ]
                }
            }
        }
        """
    )

    assert config["strategies"]["hotonleg"]["speedCurve"][1]["temp"] == 64.99


def test_more_than_two_decimal_temperature_threshold_is_rejected():
    with pytest.raises(ValidationError):
        parse_config(
            """
            {
                "defaultStrategy": "hotonleg",
                "strategyOnDischarging": "",
                "strategies": {
                    "hotonleg": {
                        "speedCurve": [
                            {"temp": 64.999, "speed": 50}
                        ]
                    }
                }
            }
            """
        )
