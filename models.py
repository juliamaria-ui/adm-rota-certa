from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class SerializableMixin:
    def _decimal_to_float(self, value):
        if isinstance(value, Decimal):
            return float(value)
        return value


class Funcionario(Base, SerializableMixin):
    __tablename__ = "funcionarios"

    id_funcionario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    cpf: Mapped[str] = mapped_column(String(14), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    senha_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cargo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    usuario: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    locacoes = relationship("Locacao", back_populates="funcionario")

    @property
    def is_admin(self) -> bool:
        return (self.cargo or "").strip().upper() in {"ADMIN", "ADMINISTRADOR", "GERENTE"}

    def to_dict(self):
        return {
            "id_funcionario": self.id_funcionario,
            "nome": self.nome,
            "cpf": self.cpf,
            "email": self.email,
            "telefone": self.telefone,
            "cargo": self.cargo,
            "usuario": self.usuario,
        }


class Pessoa(Base):
    __tablename__ = "pessoas"
    cpf: Mapped[str] = mapped_column(String(11), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    condutor = relationship("Condutor", uselist=False, viewonly=True)


class Cliente(Base):
    __tablename__ = "clientes"
    cpf: Mapped[str] = mapped_column(ForeignKey("pessoas.cpf"), primary_key=True)
    pessoa = relationship("Pessoa", lazy="joined")
    locacoes = relationship("Locacao", back_populates="cliente", passive_deletes="all")

    @property
    def nome(self):
        return self.pessoa.nome

    def to_dict(self):
        item = self.pessoa.condutor
        return {"cpf": self.cpf, "nome": self.nome, "telefone": self.pessoa.telefone,
                "email": self.pessoa.email, "cnh": item.cnh if item else None,
                "validade_cnh": item.validade_cnh.isoformat() if item else None}


class Condutor(Base):
    __tablename__ = "condutores"
    cpf: Mapped[str] = mapped_column(ForeignKey("pessoas.cpf"), primary_key=True)
    cnh: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    validade_cnh: Mapped[object] = mapped_column(Date, nullable=False)
    pessoa = relationship("Pessoa", lazy="joined")

    def to_dict(self):
        return {"cpf": self.cpf, "nome": self.pessoa.nome, "cnh": self.cnh,
                "validade_cnh": self.validade_cnh.isoformat()}


class LocacaoCondutor(Base):
    __tablename__ = "locacao_condutor"
    id_locacao: Mapped[int] = mapped_column(ForeignKey("locacoes.id_locacao"), primary_key=True)
    cpf_condutor: Mapped[str] = mapped_column(ForeignKey("condutores.cpf"), primary_key=True)


class Manutencao(Base):
    __tablename__ = "manutencoes"
    __table_args__ = (
        CheckConstraint("tipo in ('PREVENTIVA', 'CORRETIVA')", name="ck_manutencao_tipo"),
        CheckConstraint("data_fim is null or data_fim >= data_inicio", name="ck_manutencao_datas"),
        CheckConstraint("custo >= 0", name="ck_manutencao_custo"),
    )
    id_manutencao: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placa_veiculo: Mapped[str] = mapped_column(ForeignKey("veiculos.placa"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    custo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_inicio: Mapped[object] = mapped_column(Date, nullable=False)
    data_fim: Mapped[object | None] = mapped_column(Date)

    def to_dict(self):
        return {"id_manutencao": self.id_manutencao, "placa_veiculo": self.placa_veiculo,
                "tipo": self.tipo, "descricao": self.descricao, "custo": float(self.custo),
                "data_inicio": self.data_inicio.isoformat(),
                "data_fim": self.data_fim.isoformat() if self.data_fim else None}


class Veiculo(Base, SerializableMixin):
    __tablename__ = "veiculos"
    __table_args__ = (
        CheckConstraint("status in ('DISPONIVEL', 'ALUGADO', 'MANUTENCAO')", name="ck_veiculo_status"),
        CheckConstraint("valor_diaria > 0", name="ck_veiculo_diaria"),
    )

    placa: Mapped[str] = mapped_column(String(10), primary_key=True)
    marca: Mapped[str] = mapped_column(String(50), nullable=False)
    modelo: Mapped[str] = mapped_column(String(50), nullable=False)
    ano: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_diaria: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DISPONIVEL")

    locacoes = relationship("Locacao", back_populates="veiculo", passive_deletes="all")

    def to_dict(self):
        return {
            "placa": self.placa,
            "marca": self.marca,
            "modelo": self.modelo,
            "ano": self.ano,
            "valor_diaria": self._decimal_to_float(self.valor_diaria),
            "status": self.status,
        }


class Locacao(Base, SerializableMixin):
    __tablename__ = "locacoes"
    __table_args__ = (
        CheckConstraint("status in ('ATIVA', 'FINALIZADA', 'CANCELADA')", name="ck_locacao_status"),
        CheckConstraint("data_devolucao >= data_retirada", name="ck_locacao_prevista"),
        CheckConstraint("(status = 'FINALIZADA' AND data_devolucao_real IS NOT NULL AND data_devolucao_real >= data_retirada) OR (status IN ('ATIVA','CANCELADA') AND data_devolucao_real IS NULL)", name="ck_locacao_real"),
        CheckConstraint("valor_total >= 0 and valor_diaria_contratada > 0", name="ck_locacao_valores"),
    )

    id_locacao: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cpf_cliente: Mapped[str] = mapped_column(ForeignKey("clientes.cpf"), nullable=False)
    placa_veiculo: Mapped[str] = mapped_column(String(10), ForeignKey("veiculos.placa"), nullable=False)
    id_funcionario: Mapped[int] = mapped_column(Integer, ForeignKey("funcionarios.id_funcionario"), nullable=False)
    data_retirada: Mapped[object] = mapped_column(Date, nullable=False)
    data_devolucao: Mapped[object] = mapped_column(Date, nullable=False)
    data_devolucao_real: Mapped[object | None] = mapped_column(Date)
    valor_diaria_contratada: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ATIVA")

    cliente = relationship("Cliente", back_populates="locacoes")
    veiculo = relationship("Veiculo", back_populates="locacoes")
    funcionario = relationship("Funcionario", back_populates="locacoes")
    pagamentos = relationship("Pagamento", back_populates="locacao", passive_deletes="all")
    multas = relationship("Multa", back_populates="locacao", passive_deletes="all")

    def to_list_dict(self):
        return {
            "id_locacao": self.id_locacao,
            "cliente": self.cliente.nome,
            "veiculo": self.veiculo.modelo,
            "placa": self.placa_veiculo,
            "funcionario": self.funcionario.nome,
            "data_retirada": self.data_retirada.isoformat(),
            "data_devolucao": self.data_devolucao.isoformat(),
            "valor_total": self._decimal_to_float(self.valor_total),
            "status": self.status,
        }

    def to_detail_dict(self):
        data = self.to_list_dict()
        data.update({"cpf_cliente": self.cpf_cliente, "id_funcionario": self.id_funcionario})
        return data


class Pagamento(Base, SerializableMixin):
    __tablename__ = "pagamentos"

    id_pagamento: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_locacao: Mapped[int] = mapped_column(Integer, ForeignKey("locacoes.id_locacao"), nullable=False)
    id_multa: Mapped[int | None] = mapped_column(ForeignKey("multas.id_multa"), unique=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    forma_pagamento: Mapped[str] = mapped_column(String(30), nullable=False)
    data_pagamento: Mapped[object] = mapped_column(Date, nullable=False)

    locacao = relationship("Locacao", back_populates="pagamentos")
    multa = relationship("Multa", back_populates="pagamento")

    def to_dict(self):
        return {
            "id_pagamento": self.id_pagamento,
            "id_locacao": self.id_locacao,
            "id_multa": self.id_multa,
            "tipo": "MULTA" if self.id_multa is not None else "LOCACAO",
            "valor": self._decimal_to_float(self.valor),
            "forma_pagamento": self.forma_pagamento,
            "data_pagamento": self.data_pagamento.isoformat(),
        }


class Multa(Base, SerializableMixin):
    __tablename__ = "multas"

    id_multa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_locacao: Mapped[int] = mapped_column(Integer, ForeignKey("locacoes.id_locacao"), nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_multa: Mapped[object] = mapped_column(Date, nullable=False)

    locacao = relationship("Locacao", back_populates="multas")
    pagamento = relationship("Pagamento", back_populates="multa", uselist=False,
                             passive_deletes="all", lazy="selectin")

    @property
    def status(self):
        return "ACERTADA" if self.pagamento is not None else "PENDENTE"

    def to_dict(self):
        return {
            "id_multa": self.id_multa,
            "id_locacao": self.id_locacao,
            "motivo": self.motivo,
            "valor": self._decimal_to_float(self.valor),
            "data_multa": self.data_multa.isoformat(),
            "status": self.status,
        }


# =====================================================================
# Entidades Mapeadas a partir de Views SQL (Somente Leitura)
# =====================================================================

class VwLocacaoDetalhada(Base, SerializableMixin):
    __tablename__ = "vw_locacoes_detalhadas"
    __table_args__ = {"extend_existing": True}

    id_locacao: Mapped[int] = mapped_column(Integer, primary_key=True)
    status_locacao: Mapped[str] = mapped_column(String(20))
    data_retirada: Mapped[object] = mapped_column(Date)
    data_devolucao: Mapped[object] = mapped_column(Date)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cpf_cliente: Mapped[str] = mapped_column(String(14))
    nome_cliente: Mapped[str] = mapped_column(String(100))
    telefone_cliente: Mapped[str | None] = mapped_column(String(20), nullable=True)
    placa_veiculo: Mapped[str] = mapped_column(String(10))
    marca_veiculo: Mapped[str] = mapped_column(String(50))
    modelo_veiculo: Mapped[str] = mapped_column(String(50))
    valor_diaria: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    id_funcionario: Mapped[int] = mapped_column(Integer)
    nome_funcionario: Mapped[str] = mapped_column(String(100))
    total_pago: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_multas: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    saldo: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    data_devolucao_real: Mapped[object | None] = mapped_column(Date)

    def to_dict(self):
        return {
            "id_locacao": self.id_locacao,
            "status": self.status_locacao,
            "data_retirada": self.data_retirada.isoformat() if self.data_retirada else None,
            "data_devolucao": self.data_devolucao.isoformat() if self.data_devolucao else None,
            "valor_total": self._decimal_to_float(self.valor_total),
            "cpf_cliente": self.cpf_cliente,
            "cliente": self.nome_cliente,
            "telefone_cliente": self.telefone_cliente,
            "placa": self.placa_veiculo,
            "marca": self.marca_veiculo,
            "veiculo": self.modelo_veiculo,
            "valor_diaria": self._decimal_to_float(self.valor_diaria),
            "id_funcionario": self.id_funcionario,
            "funcionario": self.nome_funcionario,
            "total_pago": self._decimal_to_float(self.total_pago),
            "total_multas": self._decimal_to_float(self.total_multas),
            "saldo": self._decimal_to_float(self.saldo),
            "data_devolucao_prevista": self.data_devolucao.isoformat(),
            "data_devolucao_real": self.data_devolucao_real.isoformat() if self.data_devolucao_real else None,
        }


class VwVeiculoDisponivel(Base, SerializableMixin):
    __tablename__ = "vw_veiculos_disponiveis"
    __table_args__ = {"extend_existing": True}

    placa: Mapped[str] = mapped_column(String(10), primary_key=True)
    marca: Mapped[str] = mapped_column(String(50))
    modelo: Mapped[str] = mapped_column(String(50))
    ano: Mapped[int] = mapped_column(Integer)
    valor_diaria: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20))

    def to_dict(self):
        return {
            "placa": self.placa,
            "marca": self.marca,
            "modelo": self.modelo,
            "ano": self.ano,
            "valor_diaria": self._decimal_to_float(self.valor_diaria),
            "status": self.status,
        }


class VwFaturamentoFrota(Base, SerializableMixin):
    __tablename__ = "vw_faturamento_frota"
    __table_args__ = {"extend_existing": True}

    marca: Mapped[str] = mapped_column(String(50), primary_key=True)
    modelo: Mapped[str] = mapped_column(String(50), primary_key=True)
    total_locacoes: Mapped[int] = mapped_column(Integer)
    receita_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    def to_dict(self):
        return {
            "marca": self.marca,
            "modelo": self.modelo,
            "total_locacoes": self.total_locacoes,
            "receita_total": self._decimal_to_float(self.receita_total),
        }
