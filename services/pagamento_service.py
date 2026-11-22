from sqlalchemy import select

from database import session_scope
from errors import ConflictError, NotFoundError, ValidationError
from models import Locacao, Multa, Pagamento
from services.utils import parse_date, parse_decimal, parse_id, required, upper_string

FORMAS_VALIDAS = {"DINHEIRO", "CARTAO_CREDITO", "CARTAO_DEBITO", "PIX", "TRANSFERENCIA"}


def _validar_forma(forma: str) -> str:
    forma = upper_string(forma)
    if forma not in FORMAS_VALIDAS:
        raise ValidationError("Forma de pagamento inválida.")
    return forma


def listar_pagamentos(id_locacao: int | None = None):
    with session_scope() as db:
        query = select(Pagamento)
        if id_locacao:
            query = query.where(Pagamento.id_locacao == id_locacao)
        pagamentos = db.scalars(query.order_by(Pagamento.data_pagamento.desc(), Pagamento.id_pagamento.desc())).all()
        return [pagamento.to_dict() for pagamento in pagamentos]


def criar_pagamento(dados: dict):
    required(dados, ["id_locacao", "forma_pagamento", "data_pagamento"])
    id_locacao = parse_id(dados["id_locacao"], "id_locacao")
    id_multa = dados.get("id_multa")
    tipo = upper_string(dados.get("tipo")) or ("MULTA" if id_multa is not None else "LOCACAO")
    if tipo not in {"LOCACAO", "MULTA"}:
        raise ValidationError("Tipo de pagamento inválido.")
    if tipo == "MULTA":
        required(dados, ["id_multa"])
        id_multa = parse_id(id_multa, "id_multa")
    elif id_multa is not None:
        raise ValidationError("O vínculo com multa exige o tipo MULTA.")
    with session_scope() as db:
        locacao = db.scalar(select(Locacao).where(Locacao.id_locacao == id_locacao).with_for_update())
        if not locacao:
            raise ValidationError("Locação não encontrada.")
        if tipo == "MULTA":
            multa = db.scalar(select(Multa).where(Multa.id_multa == id_multa).with_for_update())
            if multa is None or multa.id_locacao != locacao.id_locacao:
                raise ValidationError("A multa deve pertencer à locação selecionada.")
            if db.scalar(select(Pagamento.id_pagamento).where(Pagamento.id_multa == id_multa)) is not None:
                raise ConflictError("Esta multa já possui um pagamento vinculado.")
            valor = multa.valor
            if "valor" in dados and parse_decimal(dados["valor"], "valor") != valor:
                raise ValidationError("O pagamento da multa deve ter seu valor integral.")
        else:
            required(dados, ["valor"])
            valor = parse_decimal(dados["valor"], "valor")
        pagamento = Pagamento(
            id_locacao=locacao.id_locacao,
            id_multa=id_multa,
            valor=valor,
            forma_pagamento=_validar_forma(dados["forma_pagamento"]),
            data_pagamento=parse_date(dados["data_pagamento"], "data_pagamento"),
        )
        db.add(pagamento)
        db.flush()
        return {"id_pagamento": pagamento.id_pagamento, "mensagem": "Pagamento registrado com sucesso."}


def deletar_pagamento(id_pagamento: int):
    with session_scope() as db:
        pagamento = db.get(Pagamento, id_pagamento)
        if not pagamento:
            raise NotFoundError("Pagamento não encontrado.")
        db.delete(pagamento)
        return True
