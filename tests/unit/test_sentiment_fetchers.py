import json

from btc_analyst.sentiment.bybit_longshort import parse_bybit_account_ratio
from btc_analyst.sentiment.okx_longshort import parse_okx_longshort
from btc_analyst.sentiment.fear_greed import parse_fear_greed


def test_parse_bybit_account_ratio():
    payload = {
        "retCode": 0,
        "result": {"list": [{"buyRatio": "0.61", "sellRatio": "0.39", "timestamp": "1710000000000"}]},
    }
    got = parse_bybit_account_ratio(payload)
    assert round(got["long_short_ratio"], 4) == round(0.61 / 0.39, 4)


def test_parse_okx_longshort_ratio():
    payload = {"code": "0", "data": [{"ts": "1710000000000", "ratio": "1.24"}]}
    got = parse_okx_longshort(payload)
    assert got["long_short_ratio"] == 1.24


def test_parse_fear_greed():
    payload = {"data": [{"value": "77", "value_classification": "Greed", "timestamp": "1710000000"}]}
    got = parse_fear_greed(payload)
    assert got["value"] == 77
    assert got["label"] == "Greed"
