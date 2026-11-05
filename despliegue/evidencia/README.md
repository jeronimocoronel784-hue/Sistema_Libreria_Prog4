# Evidencia del despliegue

Acá va la salida de cada caso D (D-01 a D-08), tal como se describe en
`DEPLOY.md`.

Un archivo por caso, con la salida de la consola. Para guardar una salida:

```bash
docker images > evidencia/d-01-imagenes.txt 2>&1
docker build -t libreria . 2>&1 | tee evidencia/d-02-build-run.txt
docker run -d --name libreria -p <PUERTO>:8000 --restart unless-stopped \
  --env-file libreria.env libreria 2>&1 | tee -a evidencia/d-02-build-run.txt
docker ps >> evidencia/d-02-build-run.txt
docker logs libreria >> evidencia/d-02-build-run.txt 2>&1
```

Nada de esto va dentro de la imagen: `.dockerignore` excluye `evidencia/`.
