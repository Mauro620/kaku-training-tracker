FROM node:20-slim

# pnpm viene con corepack; activarlo en la imagen evita pedirle al dev que
# instale pnpm aparte y deja la version fija via packageManager del package.json
# raiz del monorepo.
RUN corepack enable && corepack prepare pnpm@10.33.4 --activate

WORKDIR /srv

# Copiamos los package.json y el lockfile PRIMERO para que el layer de
# dependencias no se invalide cuando cambia el codigo de la app.
COPY pnpm-workspace.yaml ./pnpm-workspace.yaml
COPY package.json ./package.json
COPY pnpm-lock.yaml ./pnpm-lock.yaml
COPY apps/web/package.json ./apps/web/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
COPY packages/contracts/tsconfig.json ./packages/contracts/tsconfig.json

# pnpm fetch llena el store local con las deps del lockfile; install --offline
# usa ese store sin tocar la red.
RUN pnpm fetch \
 && pnpm install --offline --frozen-lockfile

# Ahora copiamos el codigo. pnpm install detecta que las deps ya estan y
# solo enlaza los workspaces.
COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts

ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

EXPOSE 3000

# Dev: hot reload via bind mount del compose. Para prod, sobreescribir el
# CMD en compose con `pnpm start` despues de buildear.
CMD ["pnpm", "--filter", "web", "dev"]
