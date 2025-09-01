from fastapi import FastAPI
from fastapi_pagination import add_pagination
from workout_api.routers import api_router  # Router central que inclui todos os módulos

app = FastAPI(title="Workout API")

# Registrar o router principal
app.include_router(api_router)

# Adicionar paginação global
add_pagination(app)

