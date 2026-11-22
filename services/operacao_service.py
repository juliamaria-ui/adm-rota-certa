from sqlalchemy import select

from database import session_scope
from errors import ConflictError, NotFoundError, ValidationError
from models import Manutencao, Veiculo
from services.utils import clean_string, parse_date, parse_decimal, required, upper_string


def mysql(db):
    return db.get_bind().dialect.name == "mysql"


def buscar_veiculo_para_operacao(db, placa):
    veiculo = db.scalar(select(Veiculo).where(Veiculo.placa == placa).with_for_update())
    if veiculo is None:
        raise NotFoundError("Veículo não encontrado.")
    if veiculo.status != "DISPONIVEL":
        raise ConflictError(f"Veículo indisponível: {veiculo.status}.")
    return veiculo


def listar_manutencoes(placa=None):
    with session_scope() as db:
        q = select(Manutencao)
        if placa:
            q = q.where(Manutencao.placa_veiculo == upper_string(placa))
        return [item.to_dict() for item in db.scalars(q.order_by(
            Manutencao.data_inicio.desc(), Manutencao.id_manutencao.desc()))]


def iniciar_manutencao(dados):
    required(dados, ["placa_veiculo", "data_inicio", "descricao", "custo", "tipo"])
    tipo = upper_string(dados["tipo"])
    if tipo not in {"PREVENTIVA", "CORRETIVA"}:
        raise ValidationError("Escolha manutenção preventiva ou corretiva.")
    with session_scope() as db:
        veiculo = buscar_veiculo_para_operacao(db, upper_string(dados["placa_veiculo"]))
        item = Manutencao(
            placa_veiculo=veiculo.placa, tipo=tipo, descricao=clean_string(dados["descricao"]),
            data_inicio=parse_date(dados["data_inicio"], "data_inicio"),
            custo=parse_decimal(dados["custo"], "custo"),
        )
        db.add(item)
        if not mysql(db):
            veiculo.status = "MANUTENCAO"
        db.flush()
        return item.to_dict()


def concluir_manutencao(id_manutencao, dados):
    required(dados, ["data_fim"])
    with session_scope() as db:
        item = db.scalar(select(Manutencao).where(
            Manutencao.id_manutencao == id_manutencao).with_for_update())
        if item is None:
            raise NotFoundError("Manutenção não encontrada.")
        if item.data_fim is not None:
            raise ConflictError("Manutenção já concluída.")
        fim = parse_date(dados["data_fim"], "data_fim")
        if fim < item.data_inicio:
            raise ValidationError("A data de fim não pode anteceder o início.")
        item.data_fim = fim
        if "custo" in dados:
            item.custo = parse_decimal(dados["custo"], "custo")
        if not mysql(db):
            db.get(Veiculo, item.placa_veiculo).status = "DISPONIVEL"
        db.flush()
        return item.to_dict()
