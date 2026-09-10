from pathlib import Path

from nfce_purchase_analyzer.cli import main

from fixtures import bem_maior_receipt_rounding_warning
from fixtures.pdf_builder import build_text_pdf


def test_parse_command_prints_summary_and_diagnostics(
    tmp_path: Path,
    capsys,
) -> None:
    lines, _metadata = bem_maior_receipt_rounding_warning()
    pdf_path = tmp_path / "nota.pdf"
    pdf_path.write_bytes(build_text_pdf(lines))

    exit_code = main(["parse", str(pdf_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"Arquivo: {pdf_path}" in captured.out
    assert "Data da nota: 01/03/2026 10:00:00" in captured.out
    assert "Total geral: R$ 4,48" in captured.out
    assert "Quantidade de itens: 1" in captured.out
    assert "Diagnósticos (1):" in captured.out
    assert "warning total_rounding" in captured.out


def test_parse_command_returns_error_for_missing_pdf(
    tmp_path: Path,
    capsys,
) -> None:
    missing_pdf = tmp_path / "missing.pdf"

    exit_code = main(["parse", str(missing_pdf)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "file_not_found" in captured.err