FROM python:3.12-slim

# Define diretório da aplicação
WORKDIR /app

# Copia as dependências e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos arquivos
COPY . .

# Expõe a porta padrão do Flask
EXPOSE 5000

# Comando para iniciar o app
CMD ["python", "app.py"]
