from sqlalchemy import select

from database import session_scope
from errors import ConflictError, NotFoundError, ValidationError
from models import Cliente, Condutor, Pessoa
from services.utils import clean_string, normalizar_cpf, parse_date, required


def _gravar_pessoa(db, dados):
    required(dados, ["cpf", "nome"])
    cpf = normalizar_cpf(dados["cpf"])
    pessoa = db.get(Pessoa, cpf)
    if pessoa is None:
        pessoa = Pessoa(cpf=cpf, nome=clean_string(dados["nome"]))
        db.add(pessoa)
    for campo in ("nome", "telefone", "email"):
        if campo in dados:
            setattr(pessoa, campo, clean_string(dados[campo]))
    return pessoa


def listar_clientes():
    with session_scope() as db:
        return [item.to_dict() for item in db.scalars(
            select(Cliente).join(Pessoa).order_by(Pessoa.nome)
        )]


def buscar_cliente(cpf):
    with session_scope() as db:
        cliente = db.get(Cliente, normalizar_cpf(cpf))
        if cliente is None:
            raise NotFoundError("Cliente não encontrado.")
        return cliente.to_dict()


def criar_cliente(dados):
    with session_scope() as db:
        pessoa = _gravar_pessoa(db, dados)
        if db.get(Cliente, pessoa.cpf) is not None:
            raise ConflictError("Cliente já cadastrado.")
        db.add(Cliente(pessoa=pessoa))
        _gravar_cnh(db, pessoa, dados)
        db.flush()
        return {"cpf": pessoa.cpf, "mensagem": "Cliente criado com sucesso."}


def atualizar_cliente(cpf, dados):
    with session_scope() as db:
        cliente = db.get(Cliente, normalizar_cpf(cpf))
        if cliente is None:
            raise NotFoundError("Cliente não encontrado.")
        for campo in ("nome", "telefone", "email"):
            if campo in dados:
                valor = clean_string(dados[campo])
                if campo == "nome" and not valor:
                    raise ValidationError("Informe o nome.")
                setattr(cliente.pessoa, campo, valor)
        _gravar_cnh(db, cliente.pessoa, dados)
        return {"mensagem": "Cliente atualizado com sucesso."}


def deletar_cliente(cpf):
    with session_scope() as db:
        cliente = db.get(Cliente, normalizar_cpf(cpf))
        if cliente is None:
            raise NotFoundError("Cliente não encontrado.")
        db.delete(cliente)
        return True


def _gravar_cnh(db, pessoa, dados):
    cnh = clean_string(dados.get("cnh"))
    validade = dados.get("validade_cnh")
    if not cnh and not validade:
        return
    required(dados, ["cnh", "validade_cnh"])
    condutor = db.get(Condutor, pessoa.cpf)
    if condutor is None:
        condutor = Condutor(pessoa=pessoa)
        db.add(condutor)
    condutor.cnh = cnh
    condutor.validade_cnh = parse_date(validade, "validade_cnh")


def listar_condutores():
    with session_scope() as db:
        return [item.to_dict() for item in db.scalars(
            select(Condutor).join(Pessoa).order_by(Pessoa.nome)
        )]


def salvar_condutor(dados):
    required(dados, ["cnh", "validade_cnh"])
    with session_scope() as db:
        pessoa = _gravar_pessoa(db, dados)
        _gravar_cnh(db, pessoa, dados)
        db.flush()
        return {"cpf": pessoa.cpf, "mensagem": "Condutor registrado com sucesso."}
