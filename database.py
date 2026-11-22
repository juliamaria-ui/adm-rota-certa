from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, event, func, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from werkzeug.security import generate_password_hash

from config import Config
from errors import ConflictError

Base = declarative_base()
engine = None
SessionLocal = None

VEICULOS_INICIAIS = [
    {"placa": "ABC1A23", "marca": "Toyota", "modelo": "Corolla", "ano": 2022, "valor_diaria": 180.00, "status": "DISPONIVEL"},
    {"placa": "DEF2B34", "marca": "Honda", "modelo": "Civic", "ano": 2021, "valor_diaria": 175.00, "status": "DISPONIVEL"},
    {"placa": "GHI3C45", "marca": "Chevrolet", "modelo": "Onix", "ano": 2023, "valor_diaria": 120.00, "status": "DISPONIVEL"},
    {"placa": "JKL4D56", "marca": "Hyundai", "modelo": "HB20", "ano": 2022, "valor_diaria": 115.00, "status": "DISPONIVEL"},
    {"placa": "MNO5E67", "marca": "Volkswagen", "modelo": "Polo", "ano": 2023, "valor_diaria": 135.00, "status": "DISPONIVEL"},
    {"placa": "PQR6F78", "marca": "Fiat", "modelo": "Argo", "ano": 2021, "valor_diaria": 100.00, "status": "DISPONIVEL"},
]


def _engine_options(database_url: str) -> dict:
    options = {"future": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    if database_url.startswith("mysql"):
        options["pool_pre_ping"] = True
        options["pool_recycle"] = 280
    return options


def _ensure_mysql_database(database_url: str):
    if not database_url.startswith("mysql") or not Config.MYSQL_AUTO_CREATE_DATABASE:
        return

    from sqlalchemy.engine.url import make_url

    url = make_url(database_url)
    database_name = url.database
    if not database_name:
        return

    server_url = url._replace(database=None)
    server_engine = create_engine(server_url, **_engine_options(database_url))
    safe_database_name = database_name.replace("`", "``")

    try:
        with server_engine.begin() as connection:
            connection.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{safe_database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
    finally:
        server_engine.dispose()


def _parse_sql_statements(content: str) -> list[str]:
    lines = content.splitlines()
    statements = []
    current_stmt = []
    delimiter = ";"

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.upper().startswith("DELIMITER"):
            parts = stripped.split()
            if len(parts) >= 2:
                delimiter = parts[1]
            continue

        current_stmt.append(line)
        joined = "\n".join(current_stmt).strip()
        if joined.endswith(delimiter):
            clean_stmt = joined[:-len(delimiter)].strip()
            if clean_stmt:
                statements.append(clean_stmt)
            current_stmt = []

    if current_stmt:
        remaining = "\n".join(current_stmt).strip()
        if remaining:
            statements.append(remaining)

    return statements


def _run_mysql_scripts(engine):
    sql_dir = Path(__file__).resolve().parent / "sql"
    with engine.begin() as connection:
        catalogo = {
            "INDEX": ("STATISTICS", "INDEX_NAME", "TABLE_SCHEMA"),
            "VIEW": ("VIEWS", "TABLE_NAME", "TABLE_SCHEMA"),
            "PROCEDURE": ("ROUTINES", "ROUTINE_NAME", "ROUTINE_SCHEMA"),
            "TRIGGER": ("TRIGGERS", "TRIGGER_NAME", "TRIGGER_SCHEMA"),
        }
        for name in ("02_indexes.sql", "03_views.sql", "04_procedures.sql", "05_triggers.sql"):
            content = (sql_dir / name).read_text(encoding="utf-8")
            for stmt in _parse_sql_statements(content):
                _, tipo, objeto, *_ = stmt.split(maxsplit=3)
                objeto = objeto.split("(")[0]
                tabela, coluna, schema = catalogo[tipo]
                existe = connection.scalar(text(
                    f"SELECT 1 FROM INFORMATION_SCHEMA.{tabela} "
                    f"WHERE {schema} = DATABASE() AND {coluna} = :objeto LIMIT 1"
                ), {"objeto": objeto})
                if not existe:
                    connection.exec_driver_sql(stmt)


def _run_sqlite_views(engine):
    source = (Path(__file__).resolve().parent / "sql" / "03_views.sql").read_text(encoding="utf-8")
    with engine.begin() as connection:
        for stmt in _parse_sql_statements(source):
            stmt = stmt.replace("CREATE VIEW ", "CREATE VIEW IF NOT EXISTS ").replace("GREATEST(", "MAX(")
            connection.exec_driver_sql(stmt)


def _migrar_pagamentos_multas(engine):
    """Adiciona o vínculo sem atribuir pagamentos antigos a multas por inferência."""
    inspector = inspect(engine)
    if "id_multa" in {c["name"] for c in inspector.get_columns("pagamentos")}:
        return
    with engine.begin() as connection:
        if engine.dialect.name == "mysql":
            connection.exec_driver_sql(
                "ALTER TABLE pagamentos ADD COLUMN id_multa INTEGER NULL, "
                "ADD CONSTRAINT uq_pagamentos_multa UNIQUE (id_multa), "
                "ADD CONSTRAINT fk_pagamentos_multa FOREIGN KEY (id_multa) REFERENCES multas (id_multa)"
            )
        else:
            connection.exec_driver_sql(
                "ALTER TABLE pagamentos ADD COLUMN id_multa INTEGER REFERENCES multas (id_multa)"
            )
            connection.exec_driver_sql("CREATE UNIQUE INDEX uq_pagamentos_multa ON pagamentos (id_multa)")


def init_db(database_url: str | None = None, reset: bool = False):
    global engine, SessionLocal
    url = database_url or Config.DATABASE_URL
    _ensure_mysql_database(url)
    engine = create_engine(url, **_engine_options(url))

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    from models import Funcionario, Veiculo

    tables_to_create = [t for name, t in Base.metadata.tables.items() if not name.startswith("vw_")]
    inspector = inspect(engine)
    if reset:
        with engine.begin() as connection:
            for view in ("vw_faturamento_frota", "vw_locacoes_detalhadas", "vw_veiculos_disponiveis"):
                connection.exec_driver_sql(f"DROP VIEW IF EXISTS {view}")
        Base.metadata.drop_all(bind=engine, tables=tables_to_create)
    elif inspector.has_table("locacoes"):
        campos = {c["name"] for c in inspector.get_columns("locacoes")}
        if not {"data_devolucao_real", "valor_diaria_contratada"} <= campos:
            raise RuntimeError("Esquema legado detectado. Configure DB_DATABASE=locadora_bd2 para a versão revisada.")
    Base.metadata.create_all(bind=engine, tables=tables_to_create)
    _migrar_pagamentos_multas(engine)

    # Execução das rotinas avançadas de BD2
    if engine.dialect.name == "mysql":
        _run_mysql_scripts(engine)
    elif engine.dialect.name == "sqlite":
        _run_sqlite_views(engine)

    SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True))
    seed_admin(Funcionario)
    seed_veiculos(Veiculo)


def seed_admin(Funcionario):
    session = SessionLocal()
    try:
        exists = session.query(Funcionario).filter(Funcionario.usuario == Config.ADMIN_USUARIO).first()
        if exists:
            return
        admin = Funcionario(
            nome=Config.ADMIN_NOME,
            cpf=Config.ADMIN_CPF,
            email=Config.ADMIN_EMAIL,
            telefone="",
            cargo="ADMIN",
            usuario=Config.ADMIN_USUARIO,
            senha_hash=generate_password_hash(Config.ADMIN_SENHA),
        )
        session.add(admin)
        session.commit()
    except IntegrityError:
        session.rollback()
    finally:
        session.close()


def seed_veiculos(Veiculo):
    session = SessionLocal()
    try:
        total_veiculos = session.scalar(select(func.count(Veiculo.placa))) or 0
        if total_veiculos > 0:
            return
        for item in VEICULOS_INICIAIS:
            session.add(Veiculo(**item))
        session.commit()
    except IntegrityError:
        session.rollback()
    finally:
        session.close()


@contextmanager
def session_scope():
    if SessionLocal is None:
        init_db()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Registro duplicado ou vinculado a outro cadastro.") from exc
    except DBAPIError as exc:
        session.rollback()
        if exc.orig.args and exc.orig.args[0] == 1644:
            raise ConflictError(str(exc.orig.args[1])) from exc
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def remove_session(_exception=None):
    if SessionLocal is not None:
        SessionLocal.remove()
