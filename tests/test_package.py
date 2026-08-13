import nfce_purchase_analyzer


def test_package_exposes_basic_metadata() -> None:
    assert nfce_purchase_analyzer.__name__ == "nfce_purchase_analyzer"
    assert isinstance(nfce_purchase_analyzer.__version__, str)
    assert nfce_purchase_analyzer.__version__
