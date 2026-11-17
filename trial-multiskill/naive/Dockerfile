FROM python:3.12
WORKDIR /app
COPY . .
EXPOSE 8000
CMD ["python", "-m", "docket.serve", "--db", "/app/docket.db", "--port", "8000"]
