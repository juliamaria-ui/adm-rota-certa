import os

import pytest
from app import create_app
from database import init_db, SessionLocal
from models import Funcionario, Cliente, Veiculo, Locacao, Pagamento, Multa


@pytest.fixture
def app():
    test_config = {
        "TESTING": True,
        "DATABASE_URL": os.environ.get('LOCADORA_TEST_DATABASE', 'sqlite:///:memory:'),
        "RESET_DATABASE": True,
        "SECRET_KEY": "test-secret-key",
    }
    assert test_config['DATABASE_URL'].split('?')[0].endswith((':memory:', '/locadora_teste'))
    app = create_app(overrides=test_config)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    # Realiza login do admin padrão
    res = client.post("/funcionarios/login", json={
        "usuario": "admin",
        "senha": "admin123"
    })
    assert res.status_code == 200
    return client


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json["status"] == "ok"


def test_auth_login_e_logout(client):
    # Login inválido
    res = client.post("/funcionarios/login", json={"usuario": "admin", "senha": "wrong"})
    assert res.status_code == 400

    # Login válido
    res = client.post("/funcionarios/login", json={"usuario": "admin", "senha": "admin123"})
    assert res.status_code == 200
    assert res.json["usuario"] == "admin"

    # Checa usuário logado
    res = client.get("/funcionarios/me")
    assert res.status_code == 200
    assert res.json["authenticated"] is True
    assert res.json["user"]["usuario"] == "admin"

    # Logout
    res = client.post("/funcionarios/logout")
    assert res.status_code == 200

    # Acesso pós logout
    res = client.get("/funcionarios/me")
    assert res.status_code == 200
    assert res.json["authenticated"] is False
    assert res.json["user"] is None


def test_crud_cliente(auth_client):
    # Criar cliente
    novo_cliente = {
        "cpf": "123.456.789-00",
        "nome": "Maria Silva",
        "telefone": "38999998888",
        "email": "maria@exemplo.com",
        "cnh": "12345678900", "validade_cnh": "2030-11-23"
    }
    res = auth_client.post("/clientes/", json=novo_cliente)
    assert res.status_code == 201

    # Listar clientes
    res = auth_client.get("/clientes/")
    assert res.status_code == 200
    cpfs = [c["cpf"] for c in res.json]
    assert "12345678900" in cpfs

    # Buscar cliente por CPF
    res = auth_client.get("/clientes/123.456.789-00")
    assert res.status_code == 200
    assert res.json["nome"] == "Maria Silva"

    # Atualizar cliente
    res = auth_client.put("/clientes/123.456.789-00", json={"nome": "Maria Silva Santos"})
    assert res.status_code == 200

    # Deletar cliente
    res = auth_client.delete("/clientes/123.456.789-00")
    assert res.status_code == 200


def test_veiculo_e_locacao_fluxo_completo(auth_client):
    # 1. Cadastra Cliente
    auth_client.post("/clientes/", json={
        "cpf": "111.222.333-44",
        "nome": "João Souza",
        "telefone": "38988887777",
        "email": "joao@exemplo.com",
        "cnh": "99887766554", "validade_cnh": "2030-11-23"
    })

    # 2. Cadastra Veículo
    auth_client.post("/veiculos/", json={
        "placa": "TST1234",
        "marca": "Toyota",
        "modelo": "Yaris",
        "ano": 2023,
        "valor_diaria": 150.00,
        "status": "DISPONIVEL"
    })

    # 3. Cria Locação Ativa
    locacao_payload = {
        "cpf_cliente": "111.222.333-44",
        "placa_veiculo": "TST1234",
        "id_funcionario": 1,
        "data_retirada": "2026-11-20",
        "data_devolucao": "2026-11-23",
        "status": "ATIVA"
    }
    res = auth_client.post("/locacoes/", json=locacao_payload)
    assert res.status_code == 201
    id_locacao = res.json["id_locacao"]
    assert res.json["valor_total"] == 450.00  # 3 diárias * 150.00

    # 4. Verifica se o veículo ficou ALUGADO
    res = auth_client.get("/veiculos/TST1234")
    assert res.status_code == 200
    assert res.json["status"] == "ALUGADO"

    # 5. Adiciona Multa à Locação
    res = auth_client.post("/multas/", json={
        "id_locacao": id_locacao,
        "motivo": "Devolução com combustível abaixo do nível",
        "valor": 80.00,
        "data_multa": "2026-11-23"
    })
    assert res.status_code == 201

    # 6. Adiciona Pagamento
    res = auth_client.post("/pagamentos/", json={
        "id_locacao": id_locacao,
        "valor": 530.00,
        "forma_pagamento": "PIX",
        "data_pagamento": "2026-11-23"
    })
    assert res.status_code == 201

    # 7. Finaliza a Locação (chama Procedure no MySQL / Fallback no SQLite)
    res = auth_client.post(f"/locacoes/{id_locacao}/finalizar", json={"data_devolucao_real": "2026-11-23"})
    assert res.status_code == 200

    # 8. Verifica se a locação foi finalizada e o valor consolidado
    res = auth_client.get(f"/locacoes/{id_locacao}")
    assert res.status_code == 200
    assert res.json["status"] == "FINALIZADA"
    assert res.json["valor_total"] == 530.00  # 450 (diárias) + 80 (multa)

    # 9. Verifica se o veículo voltou a ficar DISPONIVEL
    res = auth_client.get("/veiculos/TST1234")
    assert res.status_code == 200
    assert res.json["status"] == "DISPONIVEL"


def test_dashboard_views(auth_client):
    res = auth_client.get("/dashboard/")
    assert res.status_code == 200
    data = res.json
    assert "counts" in data
    assert "latest" in data
    assert "views" in data
    assert "locacoes_detalhadas" in data["views"]
    assert "veiculos_disponiveis" in data["views"]
    assert "faturamento_frota" in data["views"]

def test_diaria_contratada_condutores_e_manutencao(auth_client):
    http = auth_client

    assert http.post("/clientes/", json={"cpf": "10000000001", "nome": "Titular sem CNH"}).status_code == 201
    for cpf, validade in [("10000000002", "2030-01-01"), ("10000000003", "2030-01-01"),
                          ("10000000004", "2026-01-01")]:
        assert http.post("/condutores/", json={"cpf": cpf, "nome": f"Condutor {cpf}",
                         "cnh": cpf, "validade_cnh": validade}).status_code == 201

    dados = {"cpf_cliente": "10000000001", "placa_veiculo": "ABC1A23",
             "id_funcionario": 1, "data_retirada": "2026-11-20",
             "data_devolucao_prevista": "2026-11-23"}

    assert http.post("/locacoes/", json={**dados, "condutores": ["10000000004"]}).status_code == 400
    assert http.get("/veiculos/ABC1A23").json["status"] == "DISPONIVEL"


    dados["condutores"] = ["10000000002", "10000000003"]
    abertura = http.post("/locacoes/", json=dados)
    assert abertura.status_code == 201, abertura.json
    contrato = abertura.json["id_locacao"]
    assert http.get(f"/locacoes/{contrato}").json["condutores"] == dados["condutores"]
    assert http.post("/locacoes/", json=dados).status_code == 409

    manutencao = {"placa_veiculo": "ABC1A23", "tipo": "PREVENTIVA",
                  "descricao": "Revisão", "data_inicio": "2026-11-24", "custo": 50}
    assert http.post("/manutencoes/", json=manutencao).status_code == 409
    assert http.put("/veiculos/ABC1A23", json={"status": "DISPONIVEL"}).status_code == 400
    assert http.put("/veiculos/ABC1A23", json={"valor_diaria": 220}).status_code == 200

    assert http.post(f"/locacoes/{contrato}/finalizar", json={"data_devolucao_real": "2026-11-24"}).status_code == 200
    assert http.get(f"/locacoes/{contrato}").json["valor_total"] == 720
    assert http.post("/multas/", json={"id_locacao": contrato, "motivo": "Infração",
                     "valor": 30, "data_multa": "2026-11-24"}).status_code == 201
    assert http.get(f"/locacoes/{contrato}").json["saldo"] == 750
    assert http.delete(f"/locacoes/{contrato}").status_code == 409

    resultado = http.post("/manutencoes/", json=manutencao)
    assert resultado.status_code == 201, resultado.json
    assert http.get("/veiculos/ABC1A23").json["status"] == "MANUTENCAO"
    assert http.post("/locacoes/", json=dados).status_code == 409
    manut_id = resultado.json["id_manutencao"]
    assert http.put(f"/manutencoes/{manut_id}", json={"data_fim": "2026-11-25"}).status_code == 200
    assert http.get("/veiculos/ABC1A23").json["status"] == "DISPONIVEL"

    outra = http.post("/locacoes/", json={**dados, "data_retirada": "2026-11-25",
                                         "data_devolucao_prevista": "2026-11-25"})
    assert outra.status_code == 201
    nova = outra.json["id_locacao"]
    assert http.delete(f"/locacoes/{nova}").status_code == 200
    assert http.get(f"/locacoes/{nova}").json["status"] == "CANCELADA"
    assert http.get("/veiculos/ABC1A23").json["status"] == "DISPONIVEL"


@pytest.fixture
def contrato_multa(auth_client):
    assert auth_client.post("/clientes/", json={
        "cpf": "12345678901", "nome": "Cliente multas", "cnh": "12345678901",
        "validade_cnh": "2030-01-01"
    }).status_code == 201
    response = auth_client.post("/locacoes/", json={
        "cpf_cliente": "12345678901", "placa_veiculo": "DEF2B34", "id_funcionario": 1,
        "data_retirada": "2026-11-20", "data_devolucao_prevista": "2026-11-23"
    })
    assert response.status_code == 201, response.json
    return response.json["id_locacao"]


def registrar_multa(http, contrato, data="2026-11-21"):
    return http.post("/multas/", json={
        "id_locacao": contrato, "motivo": "Infração", "valor": 80, "data_multa": data
    })


@pytest.mark.parametrize("devolucao_real", [None, "2026-11-22", "2026-11-25"])
def test_periodo_inclusivo_multa(auth_client, contrato_multa, devolucao_real):
    from datetime import date, timedelta

    http, contrato = auth_client, contrato_multa
    if devolucao_real:
        assert http.post(f"/locacoes/{contrato}/finalizar", json={
            "data_devolucao_real": devolucao_real
        }).status_code == 200
    fim = date.fromisoformat(devolucao_real or "2026-11-23")
    for dia in ["2026-11-20", fim.isoformat()]:
        assert registrar_multa(http, contrato, dia).status_code == 201
    for dia in ["2026-11-19", (fim + timedelta(days=1)).isoformat()]:
        assert registrar_multa(http, contrato, dia).status_code == 400
    assert len(http.get(f"/multas/?id_locacao={contrato}").json) == 2


def test_pagamento_multa_status_duplicidade_e_exclusao(auth_client, contrato_multa):
    http, contrato = auth_client, contrato_multa
    multa = registrar_multa(http, contrato).json["id_multa"]
    outra = registrar_multa(http, contrato).json["id_multa"]
    payload = {"tipo": "MULTA", "id_locacao": contrato, "id_multa": multa,
               "forma_pagamento": "PIX", "data_pagamento": "2026-11-23"}

    def status():
        return {m["id_multa"]: m["status"] for m in http.get(f"/multas/?id_locacao={contrato}").json}

    assert status() == {multa: "PENDENTE", outra: "PENDENTE"}
    saldo = http.get(f"/locacoes/{contrato}").json["saldo"]
    for valor in [40, 81]:
        assert http.post("/pagamentos/", json={**payload, "valor": valor}).status_code == 400
    response = http.post("/pagamentos/", json=payload)
    assert response.status_code == 201, response.json
    pagamento = response.json["id_pagamento"]
    pago = http.get(f"/pagamentos/?id_locacao={contrato}").json[0]
    assert (pago["valor"], pago["tipo"], pago["id_multa"]) == (80, "MULTA", multa)
    assert status() == {multa: "ACERTADA", outra: "PENDENTE"}
    assert http.get(f"/locacoes/{contrato}").json["saldo"] == saldo - 80
    assert http.post("/pagamentos/", json=payload).status_code == 409
    assert http.delete(f"/multas/{multa}").status_code == 409
    assert http.delete(f"/pagamentos/{pagamento}").status_code == 200
    assert status() == {multa: "PENDENTE", outra: "PENDENTE"}
    assert http.get(f"/locacoes/{contrato}").json["saldo"] == saldo
    assert http.post("/pagamentos/", json={**payload, "valor": 80}).status_code == 201


def test_pagamento_sem_vinculo_nao_acerta_multa(auth_client, contrato_multa):
    registrar_multa(auth_client, contrato_multa)
    assert auth_client.post("/pagamentos/", json={
        "id_locacao": contrato_multa, "valor": 80, "forma_pagamento": "PIX",
        "data_pagamento": "2026-11-23"
    }).status_code == 201
    assert auth_client.get(f"/multas/?id_locacao={contrato_multa}").json[0]["status"] == "PENDENTE"


def test_pagamento_exige_multa_da_mesma_locacao(auth_client, contrato_multa):
    http = auth_client
    multa = registrar_multa(http, contrato_multa).json["id_multa"]
    outra = http.post("/locacoes/", json={
        "cpf_cliente": "12345678901", "placa_veiculo": "GHI3C45", "id_funcionario": 1,
        "data_retirada": "2026-11-20", "data_devolucao_prevista": "2026-11-23"
    }).json["id_locacao"]
    payload = {"tipo": "MULTA", "id_locacao": outra, "id_multa": multa,
               "valor": 80, "forma_pagamento": "PIX", "data_pagamento": "2026-11-23"}
    assert http.post("/pagamentos/", json=payload).status_code == 400
    for identificador in [None, "", "inválido", True, 1.5, -1, 999999]:
        assert http.post("/pagamentos/", json={**payload, "id_multa": identificador}).status_code == 400
    assert http.get(f"/pagamentos/?id_locacao={outra}").json == []


def test_alteracao_devolucao_preserva_periodo_multas(auth_client, contrato_multa):
    http, contrato = auth_client, contrato_multa
    registrar_multa(http, contrato, "2026-11-23")
    assert http.put(f"/locacoes/{contrato}", json={"data_devolucao": "2026-11-22"}).status_code == 400
    assert http.post(f"/locacoes/{contrato}/finalizar", json={"data_devolucao_real": "2026-11-22"}).status_code == 400
    assert http.get(f"/locacoes/{contrato}").json["status"] == "ATIVA"
    assert http.get("/veiculos/DEF2B34").json["status"] == "ALUGADO"
    assert http.post(f"/locacoes/{contrato}/finalizar", json={"data_devolucao_real": "2026-11-23"}).status_code == 200


def test_migracao_vinculo_preserva_pagamentos_existentes():
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.exc import IntegrityError
    from database import _migrar_pagamentos_multas

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.exec_driver_sql("CREATE TABLE multas (id_multa INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE pagamentos (id_pagamento INTEGER PRIMARY KEY, valor NUMERIC)")
        conn.exec_driver_sql("INSERT INTO pagamentos VALUES (1, 80)")
        conn.exec_driver_sql("INSERT INTO multas VALUES (1)")
    _migrar_pagamentos_multas(engine)
    _migrar_pagamentos_multas(engine)
    with engine.begin() as conn:
        assert tuple(conn.execute(text("SELECT valor, id_multa FROM pagamentos")).one()) == (80, None)
        conn.exec_driver_sql("INSERT INTO pagamentos VALUES (2, 80, 1)")
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO pagamentos VALUES (3, 80, 1)")
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO pagamentos VALUES (4, 80, 999)")
    assert inspect(engine).get_foreign_keys("pagamentos")[0]["referred_table"] == "multas"
    engine.dispose()
