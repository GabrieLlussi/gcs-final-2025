from sqlalchemy import Column, Integer, String, MetaData, Table

metadata = MetaData()

categoria = Table(
    "categoria",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("descricao", String(100), nullable=False),
)
