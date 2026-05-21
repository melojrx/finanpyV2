from pathlib import Path


def test_budget_planning_header_defines_dark_form_input_styles():
    """Wizard de planejamento deve neutralizar o branco default do Tailwind Forms."""
    template = Path("templates/budgets/planning_header.html").read_text()

    assert "{% block extra_head %}" in template
    assert ".form-input" in template
    assert "background-color: #1F2937" in template
    assert "color: #F9FAFB" in template


def test_budget_planning_header_uses_form_input_class_on_money_fields():
    template = Path("templates/budgets/planning_header.html").read_text()

    for field in [
        "id_renda_prevista",
        "id_savings_goal",
        "id_reserva_dividas",
        "id_reserva_metas",
        "id_reserva_investimentos",
    ]:
        assert field in template

    assert template.count("form-input") >= 5
