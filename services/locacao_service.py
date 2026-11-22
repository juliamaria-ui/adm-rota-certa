from datetime import date
from sqlalchemy import select, text

from database import session_scope
from errors import ConflictError, NotFoundError, ValidationError
from models import Cliente, Condutor, Funcionario, Locacao, LocacaoCondutor, Multa, Veiculo, VwLocacaoDetalhada
from services.operacao_service import buscar_veiculo_para_operacao, mysql
from services.utils import normalizar_cpf, parse_date, required, upper_string

STATUS_VALIDOS = {"ATIVA", "FINALIZADA", "CANCELADA"}


def _status(valor):
    status = upper_string(valor) or "ATIVA"
    if status not in STATUS_VALIDOS:
        raise ValidationError("Status de locação inválido.")
    return status


def _dias(retirada, devolucao):
    if devolucao < retirada:
        raise ValidationError("A devolução não pode anteceder a retirada.")
    return max((devolucao - retirada).days, 1)


def _locacao(db, identificador):
    row = db.scalar(select(Locacao).where(Locacao.id_locacao == identificador).with_for_update())
    if row is None:
        raise NotFoundError("Locação não encontrada.")
    return row


def listar_locacoes(status_filtro=None, retirada_de=None, retirada_ate=None):
    with session_scope() as db:
        query = select(VwLocacaoDetalhada)
        if status_filtro:
            query = query.where(VwLocacaoDetalhada.status_locacao == _status(status_filtro))
        if retirada_de:
            query = query.where(VwLocacaoDetalhada.data_retirada >= parse_date(retirada_de, 'retirada_de'))
        if retirada_ate:
            query = query.where(VwLocacaoDetalhada.data_retirada <= parse_date(retirada_ate, 'retirada_ate'))
        return [row.to_dict() for row in db.scalars(query.order_by(
            VwLocacaoDetalhada.data_retirada.desc(), VwLocacaoDetalhada.id_locacao.desc()))]


def buscar_locacao(id_locacao):
    with session_scope() as db:
        row = db.get(VwLocacaoDetalhada, id_locacao)
        if row is None:
            raise NotFoundError("Locação não encontrada.")
        dados = row.to_dict()
        dados["condutores"] = list(db.scalars(select(LocacaoCondutor.cpf_condutor).where(
            LocacaoCondutor.id_locacao == id_locacao
        ).order_by(LocacaoCondutor.cpf_condutor)))
        return dados


def criar_locacao(dados):
    required(dados, ["cpf_cliente", "placa_veiculo", "id_funcionario", "data_retirada"])
    if _status(dados.get("status")) != "ATIVA":
        raise ValidationError("Uma locação deve ser aberta como ATIVA.")
    retirada = parse_date(dados["data_retirada"], "data_retirada")
    prevista = parse_date(dados.get("data_devolucao_prevista") or dados.get("data_devolucao"),
                          "data_devolucao_prevista")
    dias = _dias(retirada, prevista)
    cpf = normalizar_cpf(dados["cpf_cliente"])
    placa = upper_string(dados["placa_veiculo"])
    lista = dados.get("condutores", [cpf])
    if not isinstance(lista, list) or not lista:
        raise ValidationError("Selecione pelo menos um condutor.")
    cpfs = sorted({normalizar_cpf(item) for item in lista})
    try:
        funcionario = int(dados["id_funcionario"])
    except (TypeError, ValueError) as exc:
        raise ValidationError("Funcionário inválido.") from exc

    with session_scope() as db:
        veiculo = buscar_veiculo_para_operacao(db, placa)
        if db.get(Cliente, cpf) is None or db.get(Funcionario, funcionario) is None:
            raise ValidationError("Cliente ou funcionário não cadastrado.")
        condutores = list(db.scalars(select(Condutor).where(
            Condutor.cpf.in_(cpfs)).order_by(Condutor.cpf).with_for_update()))
        if len(condutores) != len(cpfs) or any(c.validade_cnh < retirada for c in condutores):
            raise ValidationError("Todos os condutores devem ter CNH válida na retirada.")
        row = Locacao(cpf_cliente=cpf, placa_veiculo=placa, id_funcionario=funcionario,
                      data_retirada=retirada, data_devolucao=prevista,
                      valor_diaria_contratada=veiculo.valor_diaria,
                      valor_total=veiculo.valor_diaria * dias, status="ATIVA")
        db.add(row)
        if not mysql(db):
            veiculo.status = "ALUGADO"
        db.flush()
        db.add_all(LocacaoCondutor(id_locacao=row.id_locacao, cpf_condutor=c) for c in cpfs)
        return {"id_locacao": row.id_locacao, "valor_total": float(row.valor_total),
                "dias": dias, "mensagem": "Locação criada com sucesso."}


def _finalizar(db, row, real):
    if row.status != "ATIVA":
        raise ConflictError("Apenas uma locação ativa pode ser finalizada.")
    dias = _dias(row.data_retirada, real)
    _validar_periodo_multas(db, row, real)
    if mysql(db):
        db.execute(text("CALL sp_finalizar_locacao(:id, :real)"),
                   {"id": row.id_locacao, "real": real}).close()
    else:
        row.data_devolucao_real = real
        row.valor_total = row.valor_diaria_contratada * dias
        row.status = "FINALIZADA"
        row.veiculo.status = "DISPONIVEL"
    return {"mensagem": "Locação finalizada com sucesso."}


def _validar_periodo_multas(db, row, devolucao):
    fora_periodo = db.scalar(select(Multa.id_multa).where(
        Multa.id_locacao == row.id_locacao,
        (Multa.data_multa < row.data_retirada) | (Multa.data_multa > devolucao)
    ).limit(1))
    if fora_periodo is not None:
        raise ValidationError("A devolução informada deixa uma multa fora do período da locação. Corrija a multa antes de alterar a devolução.")


def finalizar_locacao(id_locacao, dados=None):
    real = parse_date((dados or {}).get("data_devolucao_real") or date.today(),
                      "data_devolucao_real")
    with session_scope() as db:
        return _finalizar(db, _locacao(db, id_locacao), real)


def atualizar_locacao(id_locacao, dados):
    with session_scope() as db:
        row = _locacao(db, id_locacao)
        if row.status != "ATIVA":
            raise ConflictError("Apenas uma locação ativa pode ser alterada.")
        status = _status(dados.get("status"))
        if status == "FINALIZADA":
            if not dados.get("data_devolucao_real"):
                raise ValidationError("Informe a data efetiva da devolução.")
            return _finalizar(db, row, parse_date(dados["data_devolucao_real"], "data_devolucao_real"))
        if status == "CANCELADA":
            row.status = status
            if not mysql(db):
                row.veiculo.status = "DISPONIVEL"
        else:
            prevista = dados.get("data_devolucao_prevista") or dados.get("data_devolucao")
            if prevista:
                prevista = parse_date(prevista, "data_devolucao_prevista")
                _validar_periodo_multas(db, row, prevista)
                row.data_devolucao = prevista
                row.valor_total = row.valor_diaria_contratada * _dias(row.data_retirada, row.data_devolucao)
        return {"mensagem": "Locação atualizada com sucesso."}


def deletar_locacao(id_locacao):
    return atualizar_locacao(id_locacao, {"status": "CANCELADA"})
