"""Contrato de la arquitectura: lo que el producto debe hacer, visto desde afuera."""

SEARCH = "search_knowledge_base"
ESCALATE = "escalate_to_human"


def ask(api, question, **extra):
    return api.post("/ask", json={"question": question, **extra})


def test_health_answers_ok(api):
    response = api.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home_page_has_the_question_form(api):
    page = api.get("/").text
    for test_id in ("question", "send", "answer", "escalation"):
        assert f'data-testid="{test_id}"' in page


def test_a_known_problem_gets_the_solution_from_the_knowledge_base(api):
    body = ask(api, "No me puedo conectar a la VPN desde mi casa").json()
    assert "KB-0001" in body["answer"]
    assert "cliente de VPN" in body["answer"]
    assert body["tools_used"] == [SEARCH]
    assert body["escalated"] is False
    assert body["team"] is None
    assert body["steps"] == 2


def test_the_problem_is_matched_without_accents_or_capitals(api):
    body = ask(api, "SE ATORO EL PAPEL EN LA IMPRESORA").json()
    assert "Atasco de papel" in body["answer"]
    assert body["escalated"] is False


def test_a_problem_without_a_solution_is_escalated_to_its_team(api):
    body = ask(api, "Mi teclado tiene teclas que no funcionan").json()
    assert body["tools_used"] == [SEARCH, ESCALATE]
    assert body["escalated"] is True
    assert body["team"] == "Soporte en sitio"
    assert "Soporte en sitio" in body["answer"]
    # Buscar y transferir: la transferencia termina sin otra llamada al modelo
    assert body["steps"] == 2


def test_an_obsolete_article_is_never_offered(api):
    body = ask(api, "Necesito instalar un programa nuevo").json()
    assert "KB-0008" not in body["answer"]
    assert body["escalated"] is True
    assert body["team"] == "Mesa de Software"


def test_asking_for_a_person_goes_straight_to_the_general_desk(api):
    body = ask(api, "Quiero hablar con una persona").json()
    assert body["tools_used"] == [ESCALATE]
    assert body["team"] == "Mesa de Servicio General"


def test_an_unrecognized_message_asks_for_more_detail(api):
    body = ask(api, "¿Qué clima hace hoy en Monterrey?").json()
    assert body["tools_used"] == [SEARCH]
    assert body["escalated"] is False
    assert "Describe tu problema" in body["answer"]


def test_a_greeting_gets_guidance_without_tools(api):
    body = ask(api, "Hola").json()
    assert body["tools_used"] == []
    assert "Describe tu problema" in body["answer"]


def test_empty_question_is_rejected(api):
    assert ask(api, "").status_code == 422


def test_blank_question_is_rejected(api):
    assert ask(api, "   ").status_code == 422


def test_too_long_question_is_rejected(api):
    assert ask(api, "a" * 2001).status_code == 422


def test_history_comes_from_the_client(api):
    history = [{"role": "user", "content": "Hola"}]
    response = ask(api, "Mi laptop no enciende", history=history)
    assert response.status_code == 200


def test_the_step_cap_stops_the_loop(api_one_step):
    body = ask(api_one_step, "No me puedo conectar a la VPN desde mi casa").json()
    assert body["steps"] == 1
    assert "No pude completar" in body["answer"]
