# Local HTTPS certificate workflow

TrailForge always runs over HTTPS on the local network.

## Default behavior

- On backend container startup, if `/certs/server.crt` and `/certs/server.key` do not exist, TrailForge generates a local self-signed certificate.
- The certificate is stored in the Docker volume `trailforge_certs`.
- Frontend and backend both consume that same cert/key pair.

This is enough to run and test offline, but browsers will warn until the cert is trusted.

## Regenerate local self-signed certs

```bash
docker compose down
docker volume rm trailforge_certs
docker compose up --build
```

## Supply your own local trusted cert

1. Generate `server.crt` and `server.key` from your local CA (for example via mkcert) with SAN entries for `localhost` and the machine hostname used on the LAN.
2. Copy them into the `trailforge_certs` volume before startup:

```bash
docker run --rm \
  -v trailforge_certs:/certs \
  -v "$(pwd)/ops/certs/local:/input:ro" \
  alpine sh -c 'cp /input/server.crt /certs/server.crt && cp /input/server.key /certs/server.key && chmod 600 /certs/server.key'
```

3. Start services:

```bash
docker compose up --build
```

When using custom certs, TrailForge will not overwrite them.
