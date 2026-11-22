from flask import Blueprint, jsonify, request

from auth import admin_required
from services.cliente_service import listar_condutores, salvar_condutor
from services.operacao_service import concluir_manutencao, iniciar_manutencao, listar_manutencoes

operacao_bp = Blueprint("operacoes_frota", __name__)


@operacao_bp.get("/condutores/")
@admin_required
def condutores():
    return jsonify(listar_condutores())


@operacao_bp.post("/condutores/")
@admin_required
def condutor():
    return jsonify(salvar_condutor(request.get_json(silent=True) or {})), 201


@operacao_bp.get("/manutencoes/")
@admin_required
def manutencoes():
    return jsonify(listar_manutencoes(request.args.get("placa")))


@operacao_bp.post("/manutencoes/")
@admin_required
def manutencao():
    return jsonify(iniciar_manutencao(request.get_json(silent=True) or {})), 201


@operacao_bp.put("/manutencoes/<int:identificador>")
@admin_required
def concluir(identificador):
    return jsonify(concluir_manutencao(identificador, request.get_json(silent=True) or {}))
