from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Body, HTTPException, status, Query, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from fastapi_pagination import Page, paginate

from workout_api.atleta.schemas import AtletaCreate, AtletaResponse, AtletaUpdate
from workout_api.atleta.models import AtletaModel
from workout_api.categorias.models import CategoriaModel
from workout_api.centro_treinamento.models import CentroTreinamentoModel
from workout_api.contrib.dependencies import DatabaseDependency

router = APIRouter(prefix="/atletas", tags=["Atletas"])

# --- Criar novo atleta ---
@router.post(
    '/',
    summary='Criar um novo atleta',
    status_code=status.HTTP_201_CREATED,
    response_model=AtletaResponse
)
async def post_atleta(
    db_session: DatabaseDependency,
    atleta_in: AtletaCreate = Body(...)
):
    categoria_nome = atleta_in.categoria.nome
    centro_treinamento_nome = atleta_in.centro_treinamento.nome

    categoria = (await db_session.execute(
        select(CategoriaModel).filter_by(nome=categoria_nome))
    ).scalars().first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'A categoria {categoria_nome} não foi encontrada.'
        )

    centro_treinamento = (await db_session.execute(
        select(CentroTreinamentoModel).filter_by(nome=centro_treinamento_nome))
    ).scalars().first()

    if not centro_treinamento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'O centro de treinamento {centro_treinamento_nome} não foi encontrado.'
        )

    atleta_model = AtletaModel(
        nome=atleta_in.nome,
        cpf=atleta_in.cpf,
        idade=atleta_in.idade,
        peso=atleta_in.peso,
        altura=atleta_in.altura,
        sexo=atleta_in.sexo,
        categoria_id=categoria.pk_id,
        centro_treinamento_id=centro_treinamento.pk_id,
        created_at=datetime.utcnow()
    )

    try:
        db_session.add(atleta_model)
        await db_session.commit()
        await db_session.refresh(atleta_model)
    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=303,
            detail=f"Já existe um atleta cadastrado com o cpf: {atleta_in.cpf}"
        )

    return AtletaResponse(
        nome=atleta_model.nome,
        centro_treinamento=centro_treinamento.nome,
        categoria=categoria.nome
    )

# --- Listar atletas com query params e paginação ---
@router.get(
    '/',
    summary='Consultar todos os Atletas',
    response_model=Page[AtletaResponse]
)
async def get_atletas(
    nome: str = Query(None, description="Filtrar pelo nome do atleta"),
    cpf: str = Query(None, description="Filtrar pelo CPF do atleta"),
    db_session: DatabaseDependency = Depends()
):
    query = await db_session.execute(select(AtletaModel))
    atletas = query.scalars().all()

    # Filtragem por query params
    if nome:
        atletas = [a for a in atletas if nome.lower() in a.nome.lower()]
    if cpf:
        atletas = [a for a in atletas if a.cpf == cpf]

    # Transformar para response customizada
    atletas_out = [
        AtletaResponse(
            nome=a.nome,
            centro_treinamento=a.centro_treinamento.nome,
            categoria=a.categoria.nome
        )
        for a in atletas
    ]

    return paginate(atletas_out)

# --- Consultar um atleta pelo id ---
@router.get(
    '/{id}',
    summary='Consulta um Atleta pelo id',
    response_model=AtletaResponse
)
async def get_atleta(id: int, db_session: DatabaseDependency = Depends()):
    atleta = (await db_session.execute(
        select(AtletaModel).filter_by(pk_id=id))
    ).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Atleta não encontrado no id: {id}'
        )

    return AtletaResponse(
        nome=atleta.nome,
        centro_treinamento=atleta.centro_treinamento.nome,
        categoria=atleta.categoria.nome
    )

# --- Atualizar atleta ---
@router.patch(
    '/{id}',
    summary='Editar um Atleta pelo id',
    response_model=AtletaResponse
)
async def patch_atleta(
    id: int,
    atleta_up: AtletaUpdate = Body(...),
    db_session: DatabaseDependency = Depends()
):
    atleta = (await db_session.execute(
        select(AtletaModel).filter_by(pk_id=id))
    ).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Atleta não encontrado no id: {id}'
        )

    # Atualizar somente campos fornecidos
    update_data = atleta_up.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(atleta, key, value)

    try:
        await db_session.commit()
        await db_session.refresh(atleta)
    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=303,
            detail=f"Já existe um atleta cadastrado com o cpf: {atleta.cpf}"
        )

    return AtletaResponse(
        nome=atleta.nome,
        centro_treinamento=atleta.centro_treinamento.nome,
        categoria=atleta.categoria.nome
    )

# --- Deletar atleta ---
@router.delete(
    '/{id}',
    summary='Deletar um Atleta pelo id',
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_atleta(id: int, db_session: DatabaseDependency = Depends()):
    atleta = (await db_session.execute(
        select(AtletaModel).filter_by(pk_id=id))
    ).scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Atleta não encontrado no id: {id}'
        )

    await db_session.delete(atleta)
    await db_session.commit()
